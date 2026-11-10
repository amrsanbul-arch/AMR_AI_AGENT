import sqlite3
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

import app.instagram_oauth as instagram
from app.main import app

client = TestClient(app)


def configured(monkeypatch, tmp_path):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("META_APP_ID", "test-app-id")
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    monkeypatch.setenv("META_REDIRECT_URI", "http://localhost:8000/api/instagram/callback")
    monkeypatch.setenv("INSTAGRAM_TOKEN_ENCRYPTION_KEY", key)
    monkeypatch.setenv("INSTAGRAM_TOKEN_DB_PATH", str(tmp_path / "private" / "instagram.sqlite3"))
    return key


def test_health_and_instagram_status_are_explicitly_not_live(monkeypatch):
    monkeypatch.delenv("META_APP_ID", raising=False)
    monkeypatch.delenv("META_APP_SECRET", raising=False)
    monkeypatch.delenv("META_REDIRECT_URI", raising=False)
    monkeypatch.delenv("INSTAGRAM_TOKEN_ENCRYPTION_KEY", raising=False)
    assert client.get("/healthz").json()["instagram"] == "not_connected"
    assert client.get("/api/instagram/status").json() == {
        "status": "not_configured", "connected": False, "provider": "instagram"
    }


def test_connect_refuses_to_start_without_owner_secrets(monkeypatch):
    monkeypatch.delenv("META_APP_ID", raising=False)
    response = client.get("/api/instagram/connect")
    assert response.status_code == 503
    assert "access_token" not in response.text


def test_connect_builds_official_minimal_scope_and_httponly_state(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    response = client.get("/api/instagram/connect", follow_redirects=False)
    assert response.status_code == 302
    url = urlparse(response.headers["location"])
    query = parse_qs(url.query)
    assert url.scheme == "https" and url.netloc == "www.instagram.com"
    assert url.path == "/oauth/authorize"
    assert query["scope"] == ["instagram_business_basic"]
    assert query["redirect_uri"] == ["http://localhost:8000/api/instagram/callback"]
    assert response.cookies[instagram.STATE_COOKIE] == query["state"][0]
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert response.headers["cache-control"] == "no-store"


def test_oauth_refuses_production_until_owner_auth_exists(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", "production")
    response = client.get("/api/instagram/connect")
    assert response.status_code == 503


def test_oauth_refuses_invalid_redirect_uri_or_encryption_key(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    monkeypatch.setenv("META_REDIRECT_URI", "http://evil.example/callback")
    assert client.get("/api/instagram/connect").status_code == 503
    monkeypatch.setenv("META_REDIRECT_URI", "http://localhost:8000/api/instagram/callback")
    monkeypatch.setenv("INSTAGRAM_TOKEN_ENCRYPTION_KEY", "dummy")
    assert client.get("/api/instagram/connect").status_code == 503


def test_callback_rejects_state_mismatch_without_network(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    response = client.get("/api/instagram/callback?code=not-a-real-code&state=wrong", cookies={instagram.STATE_COOKIE: "expected"})
    assert response.status_code == 400
    assert "not-a-real-code" not in response.text
    assert response.headers.get("set-cookie", "").startswith(f"{instagram.STATE_COOKIE}=")
    assert not (tmp_path / "private" / "instagram.sqlite3").exists()


def test_callback_mock_exchange_encrypts_token_and_returns_no_secret(monkeypatch, tmp_path):
    key = configured(monkeypatch, tmp_path)
    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            if url == instagram.SHORT_TOKEN_URL:
                return FakeResponse({"access_token": "short-test-token", "user_id": 123})
            if url == instagram.LONG_TOKEN_URL:
                return FakeResponse({"access_token": "long-test-token", "expires_in": 3600})
            if url == instagram.PROFILE_URL:
                return FakeResponse({"user_id": "123", "username": "creator_example"})
            raise AssertionError("Unexpected URL")

    monkeypatch.setattr(instagram.httpx, "Client", FakeClient)
    state = "known-test-state"
    response = client.get("/api/instagram/callback", params={"code": "mock-code", "state": state}, cookies={instagram.STATE_COOKIE: state})
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "connected" and result["username"] == "creator_example"
    assert "access_token" not in result and "short-test-token" not in response.text
    assert len(calls) == 3
    assert response.headers["cache-control"] == "no-store"
    assert "max-age=0" in response.headers["set-cookie"].lower()
    with sqlite3.connect(tmp_path / "private" / "instagram.sqlite3") as db:
        encrypted = db.execute("select encrypted_token from instagram_connection").fetchone()[0]
    assert b"long-test-token" not in encrypted
    assert Fernet(key.encode()).decrypt(encrypted).decode() == "long-test-token"
    stored = client.get("/api/instagram/status").json()
    assert stored["connected"] is True
    assert "access_token" not in stored


def test_disconnect_removes_local_encrypted_token_only(monkeypatch, tmp_path):
    key = configured(monkeypatch, tmp_path)
    settings = instagram.Settings.from_env()
    instagram._store(settings, encrypted_token=Fernet(key.encode()).encrypt(b"sample"),
                     username="example", user_id="1")
    response = client.post("/api/instagram/disconnect")
    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert "Revoke app access" in response.json()["notice"]
    assert client.get("/api/instagram/status").json()["connected"] is False
