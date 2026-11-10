from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_reports_stage_without_claiming_instagram_connection() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "stage": "content_assistant",
        "instagram": "not_connected",
    }


def test_generate_ideas_returns_three_editable_arabic_ideas() -> None:
    response = client.post(
        "/api/content/generate",
        json={"mode": "ideas", "topic": "تصوير الطعام", "audience": "أصحاب المطاعم"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["generator"] == "free_template"
    assert result["language"] == "ar"
    assert len(result["pieces"]) == 3
    assert all("تصوير الطعام" in piece["title"] for piece in result["pieces"])
    assert result["pieces"][0]["hashtags"]
    assert "نموذجًا خارجيًا" in result["notice"]


def test_generate_caption_supports_english_and_returns_hashtags() -> None:
    response = client.post(
        "/api/content/generate",
        json={"mode": "caption", "topic": "home gardening", "language": "en", "tone": "educational"},
    )

    assert response.status_code == 200
    result = response.json()
    assert len(result["pieces"]) == 1
    assert "home gardening" in result["pieces"][0]["body"]
    assert result["pieces"][0]["hashtags"]
    assert "Free editable local draft" in result["notice"]


def test_generate_reel_script_contains_scenes_and_voiceover() -> None:
    response = client.post(
        "/api/content/generate",
        json={"mode": "reel_script", "topic": "إعادة التدوير"},
    )

    assert response.status_code == 200
    piece = response.json()["pieces"][0]
    assert piece["scenes"]
    assert "التعليق الصوتي" in piece["body"]
    assert "0–3" in piece["hook"]


def test_generate_rejects_missing_topic_and_unknown_mode() -> None:
    missing_topic = client.post("/api/content/generate", json={"mode": "ideas"})
    unknown_mode = client.post(
        "/api/content/generate", json={"mode": "publish", "topic": "topic"}
    )

    assert missing_topic.status_code == 422
    assert unknown_mode.status_code == 422


def test_generate_rejects_whitespace_only_topic() -> None:
    response = client.post(
        "/api/content/generate", json={"mode": "ideas", "topic": "   "}
    )

    assert response.status_code == 422


def test_local_frontend_origin_is_allowed_by_cors() -> None:
    response = client.options(
        "/api/content/generate",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_unconfigured_site_origin() -> None:
    response = client.options(
        "/api/content/generate",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers
