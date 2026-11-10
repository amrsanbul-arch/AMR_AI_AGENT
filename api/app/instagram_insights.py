"""Read-only official Instagram Insights API integration.

All values come from the authenticated owner's Instagram Graph API token; no demo
or estimated values are substituted when Meta omits a metric.
"""
from __future__ import annotations

import re
import time

from fastapi import APIRouter, Depends, HTTPException, Query

from app.owner_auth import require_owner
from app.instagram_oauth import (
    Settings,
    _graph_get,
    _stored_access_token,
    _graph_url,
    MEDIA_FIELDS,
)

router = APIRouter(
    prefix="/api/instagram",
    tags=["instagram-insights"],
    dependencies=[Depends(require_owner)],
)
GRAPH_ROOT = "https://graph.instagram.com"
DEFAULT_GRAPH_VERSION = "v27.0"
ACCOUNT_METRICS = ("follower_count", "reach", "views", "accounts_engaged", "total_interactions")
MEDIA_METRICS = ("views", "reach", "likes", "comments", "shares", "saved", "total_interactions")


def _graph_version() -> str:
    import os
    version = os.getenv("META_GRAPH_API_VERSION", DEFAULT_GRAPH_VERSION).strip()
    if not re.fullmatch(r"v\d+\.0", version):
        raise HTTPException(status_code=503, detail="Instagram Graph API version is invalid.")
    return version


def _metric_value(payload: dict) -> int | float | None:
    total = payload.get("total_value")
    if isinstance(total, dict) and isinstance(total.get("value"), (int, float)):
        return total["value"]
    values = payload.get("values")
    if isinstance(values, list) and values:
        value = values[-1].get("value") if isinstance(values[-1], dict) else None
        if isinstance(value, (int, float)):
            return value
    return None


def _account_metric(token: str, user_id: str, metric: str, since: int, until: int, version: str) -> dict:
    endpoint = f"{GRAPH_ROOT}/{version}/{user_id}/insights"
    params = {"metric": metric}
    params.update({
        "period": "day",
        "metric_type": "time_series",
        "since": since,
        "until": until,
    })
    payload = _graph_get(endpoint, token, params=params)
    data = payload.get("data")
    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Instagram returned invalid Insights data.")
    entry = next((item for item in data if isinstance(item, dict) and item.get("name") == metric), None)
    if entry is None:
        return {"available": False, "value": None, "series": [], "reason": "not_returned"}
    series = entry.get("values") if isinstance(entry.get("values"), list) else []
    normalized_series = [
        {"value": item["value"], **({"end_time": item["end_time"]} if isinstance(item.get("end_time"), str) else {})}
        for item in series if isinstance(item, dict) and isinstance(item.get("value"), (int, float))
    ]
    value = _metric_value(entry)
    return {
        "available": value is not None or bool(normalized_series),
        "value": value,
        "series": normalized_series,
        "reason": None if value is not None or normalized_series else "not_returned",
    }


@router.get("/insights")
def instagram_account_insights(days: int = Query(default=7, ge=1, le=90)) -> dict:
    """Fetch current follower count and official daily account insights for a bounded period."""
    settings = Settings.from_env()
    if not settings.configured():
        raise HTTPException(status_code=503, detail="Instagram API is not configured.")
    token, stored = _stored_access_token(settings)
    version = _graph_version()  # fail clearly for a bad configuration before iterating metrics
    user_id = stored["user_id"]
    if not user_id.isdigit():
        raise HTTPException(status_code=503, detail="Stored Instagram account identifier is invalid.")
    until = int(time.time())
    since = until - days * 24 * 60 * 60
    metrics: dict[str, dict] = {}
    for metric in ACCOUNT_METRICS:
        try:
            metrics[metric] = _account_metric(token, user_id, metric, since, until, version)
        except HTTPException as exc:
            # Preserve partial success. The API may omit a metric for small/new accounts;
            # generic errors do not claim that the missing metric is zero.
            metrics[metric] = {
                "available": False, "value": None, "series": [],
                "reason": "api_error", "status_code": exc.status_code,
            }
    return {
        "source": "instagram_graph_api",
        "range_days": days,
        "since": since,
        "until": until,
        "fetched_at": until,
        "metrics": metrics,
    }


@router.get("/media/{media_id}/insights")
def instagram_media_insights(media_id: str) -> dict:
    """Read official insight metrics for one media ID using the owner's token."""
    if not re.fullmatch(r"[0-9]{1,40}", media_id):
        raise HTTPException(status_code=422, detail="Instagram media ID is invalid.")
    settings = Settings.from_env()
    if not settings.configured():
        raise HTTPException(status_code=503, detail="Instagram API is not configured.")
    token, stored = _stored_access_token(settings)
    version = _graph_version()
    if not stored["user_id"].isdigit():
        raise HTTPException(status_code=503, detail="Stored Instagram account identifier is invalid.")
    endpoint = f"{GRAPH_ROOT}/{version}/{media_id}/insights"
    metrics: dict[str, dict] = {}
    # Meta supports different metrics by media format and API version. Query each metric
    # separately so one unsupported metric does not hide the others; absence is not zero.
    for name in MEDIA_METRICS:
        try:
            payload = _graph_get(endpoint, token, params={"metric": name})
            data = payload.get("data")
            if not isinstance(data, list):
                metrics[name] = {"available": False, "value": None, "reason": "invalid_response"}
                continue
            item = next((row for row in data if isinstance(row, dict) and row.get("name") == name), None)
            value = _metric_value(item) if item else None
            metrics[name] = {
                "available": value is not None,
                "value": value,
                "reason": None if value is not None else "not_returned",
            }
        except HTTPException as exc:
            metrics[name] = {
                "available": False, "value": None, "reason": "api_error",
                "status_code": exc.status_code,
            }
    return {"source": "instagram_graph_api", "media_id": media_id, "metrics": metrics}


def _nonnegative_count(value: object) -> int | None:
    # Graph count fields should be whole nonnegative integers. Never coerce bools or
    # malformed/missing values into a plausible-looking zero.
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def rank_content_performance(items: list[object]) -> dict:
    """Rank a bounded official media sample by reported likes plus comments only.

    This deliberately does not call the sum an engagement rate or a complete
    interaction count. Items missing either component are excluded from rankings.
    """
    posts: list[dict] = []
    reels: list[dict] = []
    missing = 0
    valid_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        media_id = item.get("id")
        if not isinstance(media_id, str) or not re.fullmatch(r"[0-9]{1,40}", media_id):
            continue
        likes = _nonnegative_count(item.get("like_count"))
        comments = _nonnegative_count(item.get("comments_count"))
        if likes is None or comments is None:
            missing += 1
            continue
        valid_count += 1
        row = {
            "id": media_id,
            "caption": item.get("caption") if isinstance(item.get("caption"), str) else "",
            "media_type": item.get("media_type") if isinstance(item.get("media_type"), str) else None,
            "media_product_type": item.get("media_product_type") if isinstance(item.get("media_product_type"), str) else None,
            "timestamp": item.get("timestamp") if isinstance(item.get("timestamp"), str) else None,
            "permalink": item.get("permalink") if isinstance(item.get("permalink"), str) and item.get("permalink", "").startswith("https://www.instagram.com/") else None,
            "like_count": likes,
            "comments_count": comments,
            "likes_and_comments": likes + comments,
        }
        if row["media_product_type"] == "REELS":
            reels.append(row)
        else:
            posts.append(row)
    sort_key = lambda row: (-row["likes_and_comments"], row["id"])
    posts.sort(key=sort_key)
    reels.sort(key=sort_key)
    return {
        "comparable_count": valid_count,
        "missing_count_metrics": missing,
        "top_posts": posts[:5],
        "top_reels": reels[:5],
        "method": "likes_plus_comments",
        "notice": "Ranks only returned media with both official like_count and comments_count; this is not a complete interaction total, engagement rate, or performance explanation.",
    }


@router.get("/performance/content")
def instagram_content_performance(
    limit: int = Query(default=12, ge=1, le=50),
    after: str | None = Query(default=None, min_length=1, max_length=512),
) -> dict:
    """Rank recent official Instagram media by the subset of counts Graph returns."""
    settings = Settings.from_env()
    if not settings.configured():
        raise HTTPException(status_code=503, detail="Instagram API is not configured.")
    token, stored = _stored_access_token(settings)
    user_id = stored["user_id"]
    if not user_id.isdigit():
        raise HTTPException(status_code=503, detail="Stored Instagram account identifier is invalid.")
    params = {"fields": MEDIA_FIELDS, "limit": limit}
    if after:
        params["after"] = after
    payload = _graph_get(_graph_url(f"{user_id}/media"), token, params=params)
    items = payload.get("data")
    if not isinstance(items, list):
        raise HTTPException(status_code=502, detail="Instagram returned an invalid media list.")
    ranked = rank_content_performance(items)
    paging = payload.get("paging") if isinstance(payload.get("paging"), dict) else {}
    cursors = paging.get("cursors") if isinstance(paging.get("cursors"), dict) else {}
    return {
        "source": "instagram_graph_api",
        "sample_size": len([item for item in items if isinstance(item, dict)]),
        **ranked,
        "paging": {"next_after": cursors.get("after") if isinstance(cursors.get("after"), str) else None},
    }
