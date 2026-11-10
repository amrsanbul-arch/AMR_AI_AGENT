from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import strategy
from app.main import app
from app.owner_auth import require_owner

client = TestClient(app)


def _performance():
    media = [
        {"id": "11", "caption": "food photography tips", "media_product_type": "FEED", "like_count": 20, "comments_count": 3},
        {"id": "12", "caption": "food styling", "media_product_type": "FEED", "like_count": 15, "comments_count": 2},
        {"id": "13", "caption": "behind the scenes", "media_product_type": "REELS", "like_count": 33, "comments_count": 6},
        {"id": "14", "caption": "a reel", "media_product_type": "REELS", "like_count": 22, "comments_count": 4},
        {"id": "15", "caption": "missing counts", "media_product_type": "REELS", "like_count": 7},
    ]
    from app.instagram_insights import rank_content_performance
    return {"source": "instagram_graph_api", "sample_size": 5, **rank_content_performance(media)}


def _trend_report():
    return {
        "source": "Google Trends · Trending now RSS",
        "source_url": "https://trends.google.com/trending/rss?geo=EG",
        "trends": [
            {"query": "food photography", "relevance": 100, "matched_terms": ["food", "photography"], "approximate_traffic": "200+"},
            {"query": "football", "relevance": 0, "matched_terms": [], "approximate_traffic": "1000+"},
        ],
    }


def test_report_builds_cautious_recommendations_from_observed_metrics_and_search_signals():
    result = strategy.build_strategy_report(
        "food photography", "EG", _performance(), _trend_report(),
        generated_at=datetime(2026, 11, 10, tzinfo=timezone.utc),
    )
    assert result["status"] == "ready"
    assert result["official_source"] == "instagram_graph_api"
    assert result["sample_size"] == 5
    assert result["comparable_count"] == 4
    assert result["missing_metric_count"] == 1
    assert [item["query"] for item in result["trend_candidates"]] == ["food photography"]
    assert any(item["kind"] == "format_test" for item in result["recommendations"])
    search = next(item for item in result["recommendations"] if item["kind"] == "search_signal_experiment")
    assert "not establish Instagram" in search["text_en"]
    assert "audience data" in result["limitations_en"]


def test_report_labels_missing_official_data_as_insufficient_not_zero():
    result = strategy.build_strategy_report("food", "EG", None, None, official_status="not_connected", trends_status="unavailable")
    assert result["status"] == "limited"
    assert result["sample_size"] == 0
    assert result["official_source"] is None
    assert result["trends_status"] == "unavailable"
    assert "does not mean the values are zero" in result["recommendations"][0]["text_en"]
    assert any(item["kind"] == "search_signal_unavailable" for item in result["recommendations"])


def test_report_with_thin_sample_does_not_offer_a_performance_conclusion():
    performance = {"sample_size": 2, "comparable_count": 2, "missing_count_metrics": 0, "top_posts": [], "top_reels": []}
    result = strategy.build_strategy_report("coffee", "EG", performance, {"trends": []})
    assert result["status"] == "limited"
    assert result["recommendations"][0]["kind"] == "small_sample"
    assert "do not prove" not in " ".join(item["text_en"] for item in result["recommendations"])


def test_strategy_endpoint_uses_official_api_and_public_feed_separately(monkeypatch):
    app.dependency_overrides[require_owner] = lambda: None
    monkeypatch.setattr(strategy.Settings, "from_env", lambda: type("S", (), {"configured": lambda self: True})())
    monkeypatch.setattr(strategy, "_stored_access_token", lambda settings: ("token", {"user_id": "123"}))
    def fake_graph_get(url, token, params=None):
        assert "graph.instagram.com" in url
        assert params["fields"] == strategy.MEDIA_FIELDS
        return {"data": [
            {"id": "1", "caption": "coffee", "like_count": 8, "comments_count": 2, "media_product_type": "FEED"},
            {"id": "2", "caption": "coffee again", "like_count": 10, "comments_count": 1, "media_product_type": "FEED"},
            {"id": "3", "caption": "coffee reel", "like_count": 12, "comments_count": 2, "media_product_type": "REELS"},
        ]}
    monkeypatch.setattr(strategy, "_graph_get", fake_graph_get)
    async def fake_feed(geo):
        assert geo == "EG"
        return b"feed"
    monkeypatch.setattr(strategy.trends, "fetch_google_trends_feed", fake_feed)
    monkeypatch.setattr(strategy.trends, "parse_google_trends_feed", lambda feed, geo, topic: type("R", (), {"model_dump": lambda self: {"source": "Google Trends", "source_url": "https://trends.google.com/trending/rss?geo=EG", "trends": [{"query": "coffee", "relevance": 100, "matched_terms": ["coffee"]}]}})())
    response = client.post("/api/strategy/report", json={"topic": "coffee", "geo": "EG"})
    assert response.status_code == 200
    data = response.json()
    assert data["official_status"] == "available"
    assert data["trends_status"] == "available"
    assert data["trend_source"] == "Google Trends"
    assert data["comparable_count"] == 3
    app.dependency_overrides.clear()


def test_strategy_endpoint_requires_owner():
    app.dependency_overrides.clear()
    response = client.post("/api/strategy/report", json={"topic": "coffee", "geo": "EG"})
    assert response.status_code == 503


def test_unavailable_trend_feed_is_not_described_as_no_match():
    result = strategy.build_strategy_report("coffee", "EG", None, None, official_status="not_connected", trends_status="unavailable")
    assert any(item["kind"] == "search_signal_unavailable" for item in result["recommendations"])
    assert not any(item["kind"] == "no_search_match" for item in result["recommendations"])
    assert "not evidence of no interest" in next(item["text_en"] for item in result["recommendations"] if item["kind"] == "search_signal_unavailable")
