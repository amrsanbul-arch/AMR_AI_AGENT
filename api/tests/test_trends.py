from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from app import trends
from app.owner_auth import require_owner
from app.main import app

client = TestClient(app)


FEED = '''<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel>
  <item><title>تصوير الطعام</title><pubDate>Tue, 10 Nov 2026 06:20:00 -0800</pubDate>
    <ht:approx_traffic>200+</ht:approx_traffic>
    <ht:news_item><ht:news_item_title>أفكار تصوير الطعام للمطاعم</ht:news_item_title><ht:news_item_source>Example News</ht:news_item_source><ht:news_item_url>https://news.example/story</ht:news_item_url></ht:news_item>
  </item>
  <item><title>كرة القدم</title><pubDate>Tue, 10 Nov 2026 05:20:00 -0800</pubDate><ht:approx_traffic>1000+</ht:approx_traffic>
    <ht:news_item><ht:news_item_title>مباراة اليوم</ht:news_item_title><ht:news_item_source>Example News</ht:news_item_source><ht:news_item_url>javascript:alert(1)</ht:news_item_url></ht:news_item>
  </item>
</channel></rss>'''
FEED_BYTES = FEED.encode("utf-8")


def test_parse_feed_scores_transparently_and_drops_unsafe_news_links():
    result = trends.parse_google_trends_feed(
        FEED_BYTES, geo="EG", topic="تصوير الطعام",
        retrieved_at=datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc),
    )
    assert result.trend_count == 2
    assert result.trends[0].query == "تصوير الطعام"
    assert result.trends[0].relevance == 100
    assert set(result.trends[0].matched_terms) == {"تصوير", "الطعام"}
    assert result.trends[0].news[0].url == "https://news.example/story"
    unrelated = next(item for item in result.trends if item.query == "كرة القدم")
    assert unrelated.relevance == 0
    assert unrelated.news[0].url is None
    assert result.trends[0].started_at == "2026-11-10T14:20:00+00:00"
    assert "not Instagram" in result.notice


def test_rejects_doctype_and_oversized_feed():
    with pytest.raises(ValueError):
        trends.parse_google_trends_feed(b'<!DOCTYPE x [<!ENTITY a "b">]><rss/>', geo="EG", topic="topic")
    with pytest.raises(ValueError):
        trends.parse_google_trends_feed(b"x" * (trends.MAX_FEED_BYTES + 1), geo="EG", topic="topic")


def test_research_route_uses_only_validated_query_and_fixed_public_feed(monkeypatch):
    async def fake_fetch(geo):
        assert geo == "EG"
        return FEED_BYTES

    monkeypatch.setattr(trends, "fetch_google_trends_feed", fake_fetch)
    app.dependency_overrides[require_owner] = lambda: None
    response = client.get("/api/trends/research", params={"topic": "تصوير الطعام", "geo": "EG"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "Google Trends · Trending now RSS"
    assert payload["trend_count"] == 2
    assert payload["trends"][0]["relevance"] == 100
    assert response.json()["source_url"] == "https://trends.google.com/trending/rss?geo=EG"
    app.dependency_overrides.clear()


def test_research_route_requires_owner(monkeypatch):
    monkeypatch.delenv("AMR_OWNER_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("AMR_SESSION_SECRET", raising=False)
    response = client.get("/api/trends/research", params={"topic": "food", "geo": "EG"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Owner authentication is not configured."


def test_rejects_invalid_geo_and_too_short_topic():
    app.dependency_overrides[require_owner] = lambda: None
    assert client.get("/api/trends/research", params={"topic": "food", "geo": "../../x"}).status_code == 422
    assert client.get("/api/trends/research", params={"topic": "  ", "geo": "EG"}).status_code == 422
    app.dependency_overrides.clear()
