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
