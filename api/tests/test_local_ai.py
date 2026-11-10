import asyncio

from fastapi.testclient import TestClient

from app import content_generation, local_ai
from app.content import ContentRequest, generate_content
from app.main import app
from app.owner_auth import hash_owner_password
from app.reel_studio import ReelStudioRequest, generate_reel_studio

client = TestClient(app)


def configure_ollama(monkeypatch):
    monkeypatch.setenv("CONTENT_GENERATOR", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")
    monkeypatch.setenv("AMR_OWNER_PASSWORD_HASH", hash_owner_password("test-only-password-123"))
    monkeypatch.setenv("AMR_SESSION_SECRET", "test-only-session-secret-that-is-at-least-32-bytes")
    monkeypatch.setenv("APP_ENV", "development")


def owner_client(monkeypatch):
    configure_ollama(monkeypatch)
    response = client.post("/api/auth/login", json={"password": "test-only-password-123"})
    assert response.status_code == 200
    return client


def test_template_is_default_and_provider_status_never_exposes_url_or_secrets(monkeypatch):
    monkeypatch.delenv("CONTENT_GENERATOR", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://private-host:11434/secret-path")
    status = local_ai.provider_status()
    assert status == {"generator": "free_template", "model": None, "configured": False, "fallback_available": True}
    response = client.get("/api/content/provider")
    assert response.status_code == 200
    assert "private-host" not in response.text
    assert "secret-path" not in response.text
    draft = client.post("/api/content/generate", json={"mode": "caption", "topic": "coffee", "language": "en"})
    assert draft.status_code == 200
    assert draft.json()["generator"] == "free_template"


def test_public_ollama_endpoint_is_rejected(monkeypatch):
    monkeypatch.setenv("CONTENT_GENERATOR", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://example.com")
    monkeypatch.setenv("AMR_OWNER_PASSWORD_HASH", hash_owner_password("test-only-password-123"))
    monkeypatch.setenv("AMR_SESSION_SECRET", "test-only-session-secret-that-is-at-least-32-bytes")
    assert local_ai.provider_status()["configured"] is False
    assert local_ai.provider_status()["generator"] == "free_template"


def test_ollama_requires_owner_auth_and_generates_bilingual_reel(monkeypatch):
    owner_client(monkeypatch)
    request = ReelStudioRequest(topic="coffee brewing", duration_seconds=30)
    result = generate_reel_studio(request).model_dump()

    async def fake_generate_json(prompt):
        assert "Arabic fields" in prompt
        return result

    monkeypatch.setattr(content_generation, "generate_json", fake_generate_json)
    monkeypatch.setattr(content_generation, "_auth_configured", lambda: True)
    monkeypatch.setattr(local_ai, "_auth_configured", lambda: True)

    # The local-model route is not an unauthenticated public inference proxy.
    client.cookies.clear()
    unauthenticated = client.post("/api/content/reel-studio", json={"topic": "coffee brewing"})
    assert unauthenticated.status_code == 401

    signed_in = owner_client(monkeypatch)
    response = signed_in.post("/api/content/reel-studio", json={"topic": "coffee brewing", "duration_seconds": 30})
    assert response.status_code == 200
    payload = response.json()
    assert payload["generator"] == "ollama"
    assert len(payload["scenes"]) == 4
    assert payload["scenes"][0]["voiceover_ar"]
    assert payload["scenes"][0]["voiceover_en"]
    assert payload["scenes"][-1]["end_seconds"] == 30


def test_model_failure_uses_template_fallback_and_says_so(monkeypatch):
    owner_client(monkeypatch)
    monkeypatch.setattr(content_generation, "_auth_configured", lambda: True)
    monkeypatch.setattr(local_ai, "_auth_configured", lambda: True)

    async def fake_generate_json(_prompt):
        return {"not": "the requested schema"}

    monkeypatch.setattr(content_generation, "generate_json", fake_generate_json)
    response = client.post("/api/content/generate", json={"mode": "caption", "topic": "coffee", "language": "ar"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["generator"] == "free_template"
    assert "Ollama" in payload["notice"]
    assert payload["pieces"]


def test_valid_ollama_content_is_bilingual_choice_language_and_template_fallback_stays_working(monkeypatch):
    owner_client(monkeypatch)
    monkeypatch.setattr(content_generation, "_auth_configured", lambda: True)
    monkeypatch.setattr(local_ai, "_auth_configured", lambda: True)
    request = ContentRequest(mode="caption", topic="coffee", language="en")
    content = generate_content(request).model_dump()

    async def fake_generate_json(_prompt):
        return content

    monkeypatch.setattr(content_generation, "generate_json", fake_generate_json)
    generated = client.post("/api/content/generate", json={"mode": "caption", "topic": "coffee", "language": "en"})
    assert generated.status_code == 200
    assert generated.json()["generator"] == "ollama"
    assert generated.json()["language"] == "en"

    async def unavailable(_prompt):
        return None

    monkeypatch.setattr(content_generation, "generate_json", unavailable)
    fallback = client.post("/api/content/generate", json={"mode": "caption", "topic": "coffee", "language": "en"})
    assert fallback.status_code == 200
    assert fallback.json()["generator"] == "free_template"
    assert "Ollama" in fallback.json()["notice"]


def test_ollama_json_parser_handles_plain_and_fenced_json():
    assert local_ai._parse_model_json('{"ok":true}') == {"ok": True}
    assert local_ai._parse_model_json('```json\n{"ok":true}\n```') == {"ok": True}
    assert local_ai._parse_model_json("not json") is None
