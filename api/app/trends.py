from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
import unicodedata
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.owner_auth import require_owner


router = APIRouter(tags=["public trend research"])
RSS_URL = "https://trends.google.com/trending/rss"
RSS_NS = "https://trends.google.com/trending/rss"
MAX_FEED_BYTES = 512_000
MAX_ITEMS = 20
USER_AGENT = "AMR-AI-Personal-Instagram-Manager/0.5 (public Google Trends RSS reader)"


class TrendNews(BaseModel):
    title: str
    source: str | None = None
    url: str | None = None


class TrendItem(BaseModel):
    query: str
    approximate_traffic: str | None = None
    started_at: str | None = None
    relevance: int = Field(ge=0, le=100)
    matched_terms: list[str] = Field(default_factory=list)
    news: list[TrendNews] = Field(default_factory=list)


class TrendResponse(BaseModel):
    source: str
    source_url: str
    geo: str
    topic: str
    retrieved_at: str
    trend_count: int
    trends: list[TrendItem]
    notice: str


def _safe_web_url(value: str | None) -> str | None:
    if not value or len(value) > 2_000:
        return None
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        return value.strip()
    except ValueError:
        return None


def _text(parent: ET.Element, tag: str) -> str | None:
    element = parent.find(tag)
    if element is None or element.text is None:
        return None
    value = " ".join(element.text.split())
    return value[:500] or None


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", value)
    return value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))


_STOP_WORDS = {
    "the", "and", "for", "with", "from", "this", "that", "about", "what", "how", "when", "where",
    "من", "في", "عن", "على", "الى", "إلى", "ما", "كيف", "مع", "هذا", "هذه", "هو", "هي", "و",
}


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[^\W_]+", _normalize(value), flags=re.UNICODE) if len(token) > 1 and token not in _STOP_WORDS}


def _relevance(topic: str, query: str, news: list[TrendNews]) -> tuple[int, list[str]]:
    topic_tokens = _tokens(topic)
    if not topic_tokens:
        return 0, []
    query_tokens = _tokens(query)
    matched = topic_tokens & query_tokens
    if matched == topic_tokens:
        return 100, sorted(matched)
    # Related story headlines are weak supporting overlap, never treated as Instagram data.
    story_tokens = set().union(*(_tokens(item.title) for item in news)) if news else set()
    story_match = topic_tokens & story_tokens
    combined = matched | story_match
    if not combined:
        return 0, []
    title_weight = len(matched) / len(topic_tokens)
    story_weight = len(story_match) / len(topic_tokens) * 0.5
    return min(100, round((title_weight + story_weight) * 100)), sorted(combined)


def parse_google_trends_feed(xml_bytes: bytes, *, geo: str, topic: str, retrieved_at: datetime | None = None) -> TrendResponse:
    if not xml_bytes or len(xml_bytes) > MAX_FEED_BYTES:
        raise ValueError("Invalid feed size")
    upper = xml_bytes.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("XML declarations are not accepted")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("Invalid RSS feed") from exc
    source_url = f"{RSS_URL}?geo={geo}"
    items: list[TrendItem] = []
    for item in root.findall("./channel/item")[:MAX_ITEMS]:
        title = _text(item, "title")
        if not title:
            continue
        news_items: list[TrendNews] = []
        for news_node in item.findall(f"{{{RSS_NS}}}news_item")[:3]:
            news_title = _text(news_node, f"{{{RSS_NS}}}news_item_title")
            if not news_title:
                continue
            news_items.append(TrendNews(
                title=news_title,
                source=_text(news_node, f"{{{RSS_NS}}}news_item_source"),
                url=_safe_web_url(_text(news_node, f"{{{RSS_NS}}}news_item_url")),
            ))
        try:
            pub_date = _text(item, "pubDate")
            parsed_date = parsedate_to_datetime(pub_date) if pub_date else None
            if parsed_date is not None:
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                started_at = parsed_date.astimezone(timezone.utc).isoformat()
            else:
                started_at = None
        except (TypeError, ValueError, OverflowError):
            started_at = None
        relevance, matched_terms = _relevance(topic, title, news_items)
        items.append(TrendItem(
            query=title,
            approximate_traffic=_text(item, f"{{{RSS_NS}}}approx_traffic"),
            started_at=started_at,
            relevance=relevance,
            matched_terms=matched_terms,
            news=news_items,
        ))
    if not items:
        raise ValueError("No valid RSS items")
    items.sort(key=lambda trend: (trend.relevance, trend.started_at or ""), reverse=True)
    now = retrieved_at or datetime.now(timezone.utc)
    return TrendResponse(
        source="Google Trends · Trending now RSS",
        source_url=source_url,
        geo=geo,
        topic=topic,
        retrieved_at=now.astimezone(timezone.utc).isoformat(),
        trend_count=len(items),
        trends=items,
        notice=(
            "Public Google Search trends, not Instagram trends or account analytics. This RSS feed contains a small set of recent searches; "
            "traffic is an approximate bucket, and keyword overlap is a transparent relevance hint—not an AI verdict or evidence of audience demand."
        ),
    )


async def fetch_google_trends_feed(geo: str) -> bytes:
    """Fetch only the fixed public Google Trends RSS URL; no user-supplied host or proxy."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0), follow_redirects=False, trust_env=False) as client:
            async with client.stream("GET", RSS_URL, params={"geo": geo}, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml"}) as response:
                response.raise_for_status()
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_FEED_BYTES:
                        raise HTTPException(status_code=502, detail="Trend feed exceeded the safe size limit.")
                    chunks.append(chunk)
                return b"".join(chunks)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=503, detail="The public trend feed is temporarily unavailable.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not reach the public trend feed.") from exc


@router.get("/api/trends/research", response_model=TrendResponse)
async def research_trends(
    topic: str = Query(min_length=2, max_length=120),
    geo: str = Query(default="EG", pattern=r"^[A-Z]{2}$"),
    _owner: None = Depends(require_owner),
) -> TrendResponse:
    cleaned_topic = " ".join(topic.split())
    if len(cleaned_topic) < 2:
        raise HTTPException(status_code=422, detail="Topic must contain at least two non-space characters.")
    xml_bytes = await fetch_google_trends_feed(geo)
    try:
        return parse_google_trends_feed(xml_bytes, geo=geo, topic=cleaned_topic)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="The public trend feed could not be read safely.") from exc
