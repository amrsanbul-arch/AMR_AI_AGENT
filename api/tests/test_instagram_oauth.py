import sqlite3
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

import app.instagram_oauth as instagram
import app.owner_auth as owner_auth
from app.main import app


@pytest.fixture(autouse=True)
def clean_client(monkeypatch):
    owner_auth._LOGIN_ATTEMPTS.clear()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("WEB_ORIGIN", "http://localhost:3000")
    monkeypatch.setenv("AMR_SESSION_SECRET", "test-session-secret-which-is-32-bytes-long")
    monkeypatch.setenv("AMR_OWNER_PASSWORD_HASH", owner_auth.hash_owner_password("test-owner-password-long"))
    yield


def login(client):
    response = client.post("/api/auth/login", json={"password": "test-owner-password-long"},
                           headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    return response


def configured(monkeypatch, tmp_path):
    key = Fernet.generate_key().decode("ascii")
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
    with TestClient(app) as client:
        login(client)
        assert client.get("/healthz").json()["instagram"] == "not_connected"
        assert client.get("/api/instagram/status").json() == {
            "status": "not_configured", "connected": False, "provider": "instagram"
        }


def test_instagram_routes_require_owner_session(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    endpoints = [
        ("GET", "/api/instagram/status"), ("GET", "/api/instagram/connect"),
        ("GET", "/api/instagram/account"), ("GET", "/api/instagram/media"),
        ("GET", "/api/instagram/callback?code=x&state=y"), ("POST", "/api/instagram/disconnect"),
    ]
    with TestClient(app) as client:
        for method, path in endpoints:
            response = client.request(method, path)
            assert response.status_code == 401


def test_owner_login_cookie_is_httponly_and_session_status(monkeypatch):
    with TestClient(app) as client:
        assert client.get("/api/auth/session").json() == {"configured": True, "authenticated": False}
        response = login(client)
        assert response.json() == {"authenticated": True}
        cookie = response.headers["set-cookie"].lower()
        assert owner_auth.COOKIE_NAME in cookie
        assert "httponly" in cookie and "samesite=lax" in cookie and "path=/api" in cookie
        assert client.get("/api/auth/session").json()["authenticated"] is True
        assert client.post("/api/auth/logout", json={}, headers={"Origin": "http://localhost:3000"}).json() == {"authenticated": False}
        assert client.get("/api/auth/session").json()["authenticated"] is False


def test_owner_login_rejects_foreign_origin_and_limits_failures(monkeypatch):
    with TestClient(app) as client:
        bad_origin = client.post("/api/auth/login", json={"password": "bad"}, headers={"Origin": "https://evil.example"})
        assert bad_origin.status_code == 403
        for _ in range(5):
            assert client.post("/api/auth/login", json={"password": "wrong-password"}, headers={"Origin": "http://localhost:3000"}).status_code == 401
        assert client.post("/api/auth/login", json={"password": "test-owner-password-long"}, headers={"Origin": "http://localhost:3000"}).status_code == 429


def test_owner_auth_requires_config_and_rejects_tampered_session(monkeypatch):
    monkeypatch.setenv("AMR_SESSION_SECRET", "too-short")
    with TestClient(app) as client:
        assert client.get("/api/auth/session").json()["configured"] is False
        assert client.get("/api/instagram/status").status_code == 503
    monkeypatch.setenv("AMR_SESSION_SECRET", "test-session-secret-which-is-32-bytes-long")
    with TestClient(app) as client:
        client.cookies.set(owner_auth.COOKIE_NAME, "tampered")
        assert client.get("/api/instagram/status").status_code == 401


def test_connect_requires_secrets_after_login(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    monkeypatch.delenv("META_APP_ID", raising=False)
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/instagram/connect")
        assert response.status_code == 503
        assert "access_token" not in response.text


def test_connect_builds_official_minimal_scope_and_httponly_state(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    with TestClient(app) as client:
        login(client)
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


def test_oauth_requires_owner_auth_and_https_in_production(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", "production")
    with TestClient(app, base_url="https://localhost") as client:
        login(client)
        assert client.get("/api/instagram/connect").status_code == 503
    monkeypatch.setenv("META_REDIRECT_URI", "https://example.test/api/instagram/callback")
    with TestClient(app, base_url="https://localhost") as client:
        login(client)
        assert client.get("/api/instagram/connect", follow_redirects=False).status_code == 302


def test_oauth_refuses_invalid_redirect_uri_or_encryption_key(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    with TestClient(app) as client:
        login(client)
        monkeypatch.setenv("META_REDIRECT_URI", "http://evil.example/callback")
        assert client.get("/api/instagram/connect").status_code == 503
        monkeypatch.setenv("META_REDIRECT_URI", "http://localhost:8000/api/instagram/callback")
        monkeypatch.setenv("INSTAGRAM_TOKEN_ENCRYPTION_KEY", "dummy")
        assert client.get("/api/instagram/connect").status_code == 503


def test_callback_rejects_state_mismatch_without_network(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/instagram/callback?code=not-a-real-code&state=wrong", cookies={instagram.STATE_COOKIE: "expected"})
        assert response.status_code == 400
        assert "not-a-real-code" not in response.text
        assert response.headers.get("set-cookie", "").startswith(f"{instagram.STATE_COOKIE}=")
        assert not (tmp_path / "private" / "instagram.sqlite3").exists()


def test_callback_mock_exchange_encrypts_token_and_returns_no_secret(monkeypatch, tmp_path):
    key = configured(monkeypatch, tmp_path)
    calls = []

    class FakeResponse:
        def __init__(self, payload): self.payload = payload
        def raise_for_status(self): return None
        def json(self): return self.payload

    class FakeClient:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            if url == instagram.SHORT_TOKEN_URL:
                return FakeResponse({"access_token": "short-test-token", "user_id": 123})
            if url == instagram.LONG_TOKEN_URL:
                return FakeResponse({"access_token": "long-test-token", "expires_in": 3600})
            if url == instagram.PROFILE_URL:
                return FakeResponse({"user_id": "123", "username": "creator_example", "account_type": "MEDIA_CREATOR", "media_count": 8})
            raise AssertionError("Unexpected URL")

    monkeypatch.setattr(instagram.httpx, "Client", FakeClient)
    with TestClient(app) as client:
        login(client)
        state = "known-test-state"
        response = client.get("/api/instagram/callback", params={"code": "mock-code", "state": state},
                              cookies={instagram.STATE_COOKIE: state}, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "http://localhost:3000/?instagram=connected#settings"
        assert "short-test-token" not in response.text and "long-test-token" not in response.headers["location"]
        assert len(calls) == 3
        assert response.headers["cache-control"] == "no-store"
        assert "max-age=0" in response.headers["set-cookie"].lower()
        with sqlite3.connect(tmp_path / "private" / "instagram.sqlite3") as db:
            encrypted = db.execute("select encrypted_token from instagram_connection").fetchone()[0]
        assert b"long-test-token" not in encrypted
        assert Fernet(key.encode()).decrypt(encrypted).decode() == "long-test-token"
        stored = client.get("/api/instagram/status").json()
        assert stored["connected"] is True and "access_token" not in stored


def _save_fake_connection(monkeypatch, tmp_path):
    key = configured(monkeypatch, tmp_path)
    settings = instagram.Settings.from_env()
    encrypted = Fernet(key.encode()).encrypt(b"mock-graph-token")
    instagram._store(settings, encrypted_token=encrypted, username="creator_example", user_id="12345")


def test_account_read_calls_official_graph_with_encrypted_token_not_returned(monkeypatch, tmp_path):
    _save_fake_connection(monkeypatch, tmp_path)
    calls = []

    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"user_id": "12345", "username": "creator_example", "account_type": "MEDIA_CREATOR", "media_count": 7}
    class FakeClient:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            return FakeResponse()
    monkeypatch.setattr(instagram.httpx, "Client", FakeClient)
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/instagram/account")
        assert response.status_code == 200
        assert response.json() == {"provider": "instagram", "user_id": "12345", "username": "creator_example", "account_type": "MEDIA_CREATOR", "media_count": 7}
    method, url, kwargs = calls[0]
    assert method == "GET" and url == instagram.PROFILE_URL
    assert kwargs["params"]["fields"] == instagram.PROFILE_FIELDS
    assert kwargs["params"]["access_token"] == "mock-graph-token"
    assert "mock-graph-token" not in response.text


def test_media_read_limits_fields_and_returns_cursor_not_next_url(monkeypatch, tmp_path):
    _save_fake_connection(monkeypatch, tmp_path)
    calls = []
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {"data": [{"id": "m1", "caption": "hello", "media_type": "VIDEO", "permalink": "https://www.instagram.com/p/x/", "timestamp": "2026-11-01T12:00:00+0000", "access_token": "should-not-leak"}], "paging": {"next": "https://graph.instagram.com/12345/media?access_token=secret", "cursors": {"after": "cursor-next"}}}
    class FakeClient:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            return FakeResponse()
    monkeypatch.setattr(instagram.httpx, "Client", FakeClient)
    with TestClient(app) as client:
        login(client)
        response = client.get("/api/instagram/media?limit=12&after=cursor-prev")
        assert response.status_code == 200
        assert response.json() == {"data": [{"id": "m1", "caption": "hello", "media_type": "VIDEO", "permalink": "https://www.instagram.com/p/x/", "timestamp": "2026-11-01T12:00:00+0000"}], "paging": {"next_after": "cursor-next"}}
    method, url, kwargs = calls[0]
    assert method == "GET" and url == "https://graph.instagram.com/12345/media"
    assert kwargs["params"]["limit"] == 12 and kwargs["params"]["after"] == "cursor-prev"
    assert kwargs["params"]["fields"] == instagram.MEDIA_FIELDS
    assert "secret" not in response.text and "access_token" not in response.text


def test_media_rejects_arbitrary_url_and_invalid_limit(monkeypatch, tmp_path):
    _save_fake_connection(monkeypatch, tmp_path)
    with TestClient(app) as client:
        login(client)
        assert client.get("/api/instagram/media?limit=1000").status_code == 422


def test_account_and_media_return_clear_not_connected_without_network(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    with TestClient(app) as client:
        login(client)
        assert client.get("/api/instagram/account").status_code == 409
        assert client.get("/api/instagram/media").status_code == 409


def test_disconnect_removes_local_encrypted_token_only(monkeypatch, tmp_path):
    key = configured(monkeypatch, tmp_path)
    settings = instagram.Settings.from_env()
    instagram._store(settings, encrypted_token=Fernet(key.encode()).encrypt(b"sample"), username="example", user_id="1")
    with TestClient(app) as client:
        login(client)
        response = client.post("/api/instagram/disconnect", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert response.json()["connected"] is False
        assert "Revoke app access" in response.json()["notice"]
        assert client.get("/api/instagram/status").json()["connected"] is False


def test_cors_allows_credentials_only_for_configured_web_origin(monkeypatch):
    with TestClient(app) as client:
        allowed = client.options("/api/auth/session", headers={
            "Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        })
        assert allowed.status_code == 200
        assert allowed.headers.get("access-control-allow-credentials") == "true"
        assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
        denied = client.options("/api/auth/session", headers={
            "Origin": "https://evil.example", "Access-Control-Request-Method": "GET",
        })
        assert "access-control-allow-origin" not in denied.headers
