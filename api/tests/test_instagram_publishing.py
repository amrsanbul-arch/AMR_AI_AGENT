import time
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

import app.instagram_oauth as instagram
import app.instagram_publishing as publishing
import app.owner_auth as owner_auth
from app.main import app


def configure_publish(monkeypatch, tmp_path):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("META_APP_ID", "test-app-id")
    monkeypatch.setenv("META_APP_SECRET", "test-app-secret")
    monkeypatch.setenv("META_REDIRECT_URI", "http://localhost:8000/api/instagram/callback")
    monkeypatch.setenv("INSTAGRAM_TOKEN_ENCRYPTION_KEY", key)
    monkeypatch.setenv("INSTAGRAM_TOKEN_DB_PATH", str(tmp_path / "private" / "instagram.sqlite3"))
    monkeypatch.setenv("INSTAGRAM_POSTS_DB_PATH", str(tmp_path / "private" / "posts.sqlite3"))
    monkeypatch.setenv("META_GRAPH_API_VERSION", "v27.0")
    settings = instagram.Settings.from_env()
    instagram._store(settings, encrypted_token=Fernet(key.encode()).encrypt(b"mock-token"),
                     username="creator_example", user_id="12345")


def owner_login(client):
    response = client.post("/api/auth/login", json={"password": "test-owner-password-long"},
                           headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200


class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload


class FakePublisherClient:
    calls = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def request(self, method, url, **kwargs):
        type(self).calls.append((method, url, kwargs))
        if method == "POST" and url.endswith("/12345/media"):
            return FakeResponse({"id": "777"})
        if method == "GET" and url.endswith("/777"):
            return FakeResponse({"status_code": "FINISHED"})
        if method == "POST" and url.endswith("/12345/media_publish"):
            return FakeResponse({"id": "888"})
        raise AssertionError(f"Unexpected request: {method} {url}")


@pytest.fixture(autouse=True)
def owner_auth_env(monkeypatch):
    owner_auth._LOGIN_ATTEMPTS.clear()
    monkeypatch.setenv("AMR_SESSION_SECRET", "test-session-secret-which-is-32-bytes-long")
    monkeypatch.setenv("AMR_OWNER_PASSWORD_HASH", owner_auth.hash_owner_password("test-owner-password-long"))
    yield


def create(client, **overrides):
    payload = {"caption": "A caption", "media_url": "https://cdn.example.com/post.jpg", "media_type": "IMAGE"}
    payload.update(overrides)
    return client.post("/api/instagram/posts", json=payload, headers={"Origin": "http://localhost:3000"})


def test_publish_routes_require_owner_session(monkeypatch, tmp_path):
    configure_publish(monkeypatch, tmp_path)
    response = create(TestClient(app))
    assert response.status_code == 401
    assert TestClient(app).get("/api/instagram/posts").status_code == 401


def test_draft_requires_public_https_and_supported_media(monkeypatch, tmp_path):
    configure_publish(monkeypatch, tmp_path)
    with TestClient(app) as client:
        owner_login(client)
        assert create(client, media_url="http://cdn.example.com/post.jpg").status_code == 422
        assert create(client, media_url="https://127.0.0.1/post.jpg").status_code == 422
        assert create(client, media_url="https://cdn.example.com/post.jpg", media_type="STORY").status_code == 422
        assert create(client).status_code == 201


def test_publish_now_requires_explicit_approval_and_uses_official_api(monkeypatch, tmp_path):
    configure_publish(monkeypatch, tmp_path)
    FakePublisherClient.calls = []
    monkeypatch.setattr(publishing.httpx, "Client", FakePublisherClient)
    with TestClient(app) as client:
        owner_login(client)
        draft = create(client, media_type="REELS", media_url="https://cdn.example.com/clip.mp4").json()
        refused = client.post(f"/api/instagram/posts/{draft['id']}/approve", json={"approved": False, "mode": "publish_now"}, headers={"Origin": "http://localhost:3000"})
        assert refused.status_code == 400
        assert client.get("/api/instagram/posts").json()["data"][0]["state"] == "draft"
        response = client.post(f"/api/instagram/posts/{draft['id']}/approve", json={"approved": True, "mode": "publish_now"}, headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert response.json()["state"] == "published", response.json()
        assert response.json()["instagram_media_id"] == "888"
        assert all(call[1].startswith("https://graph.instagram.com/v27.0/") for call in FakePublisherClient.calls)
        create_call = FakePublisherClient.calls[0]
        assert create_call[0] == "POST" and create_call[2]["data"]["media_type"] == "REELS"
        publish_call = FakePublisherClient.calls[-1]
        assert publish_call[0] == "POST" and publish_call[2]["data"]["creation_id"] == "777"
        assert "mock-token" not in response.text


def test_schedule_requires_future_timezone_and_can_be_cancelled(monkeypatch, tmp_path):
    configure_publish(monkeypatch, tmp_path)
    FakePublisherClient.calls = []
    with TestClient(app) as client:
        owner_login(client)
        draft = create(client).json()
        bad = client.post(f"/api/instagram/posts/{draft['id']}/approve", json={"approved": True, "mode": "schedule", "scheduled_at": "2020-01-01T12:00:00Z"}, headers={"Origin": "http://localhost:3000"})
        assert bad.status_code == 422
        due = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        scheduled = client.post(f"/api/instagram/posts/{draft['id']}/approve", json={"approved": True, "mode": "schedule", "scheduled_at": due}, headers={"Origin": "http://localhost:3000"})
        assert scheduled.status_code == 200 and scheduled.json()["state"] == "scheduled"
        assert scheduled.json()["approved_at"] and scheduled.json()["scheduled_at"]
        cancelled = client.post(f"/api/instagram/posts/{draft['id']}/cancel", json={}, headers={"Origin": "http://localhost:3000"})
        assert cancelled.status_code == 200 and cancelled.json()["state"] == "cancelled"
        assert not FakePublisherClient.calls


def test_final_publish_transport_error_is_unknown_and_never_auto_claimable(monkeypatch, tmp_path):
    configure_publish(monkeypatch, tmp_path)
    draft = {"id": "e8103205-4f30-4d4f-9f43-5362f0bc0e11", "caption": "hi", "media_url": "https://cdn.example.com/a.jpg", "media_type": "IMAGE"}
    now = publishing._now()
    with publishing._db() as db:
        db.execute("INSERT INTO instagram_posts(id,caption,media_url,media_type,state,approved_hash,approved_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                   (draft["id"], draft["caption"], draft["media_url"], draft["media_type"], "publishing", publishing._content_hash(draft), now, now, now))

    class UncertainClient(FakePublisherClient):
        def request(self, method, url, **kwargs):
            if method == "POST" and url.endswith("/12345/media_publish"):
                raise httpx.ReadTimeout("ambiguous")
            return super().request(method, url, **kwargs)
    import httpx
    result = publishing._execute_claimed(draft["id"], client_factory=UncertainClient)
    assert result["state"] == "unknown", result
    assert result["error_code"] == "publish_outcome_unknown"
    assert publishing._claim(draft["id"]) is False


def test_oauth_requests_official_publish_scope(monkeypatch, tmp_path):
    configure_publish(monkeypatch, tmp_path)
    with TestClient(app) as client:
        owner_login(client)
        response = client.get("/api/instagram/connect", follow_redirects=False)
        from urllib.parse import parse_qs, urlparse
        scopes = parse_qs(urlparse(response.headers["location"]).query)["scope"][0].split(",")
        assert "instagram_business_content_publish" in scopes


def test_due_scheduled_post_is_claimed_and_published_once(monkeypatch, tmp_path):
    configure_publish(monkeypatch, tmp_path)
    FakePublisherClient.calls = []
    post = {"id": "7e4aa784-75e3-48fc-b366-5ef14466f771", "caption": "scheduled", "media_url": "https://cdn.example.com/ready.jpg", "media_type": "IMAGE"}
    now = publishing._now()
    with publishing._db() as db:
        db.execute("INSERT INTO instagram_posts(id,caption,media_url,media_type,state,scheduled_at,approved_hash,approved_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                   (post["id"], post["caption"], post["media_url"], post["media_type"], "scheduled", (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), publishing._content_hash(post), now, now, now))
    assert publishing._claim(post["id"], due_only=True) is True
    result = publishing._execute_claimed(post["id"], client_factory=FakePublisherClient)
    assert result["state"] == "published"
    assert result["instagram_media_id"] == "888"
    assert publishing._claim(post["id"], due_only=True) is False
    assert len([call for call in FakePublisherClient.calls if call[1].endswith("/media_publish")]) == 1


def test_scheduler_pause_resume_is_authenticated_and_blocks_due_claims(monkeypatch, tmp_path):
    configure_publish(monkeypatch, tmp_path)
    monkeypatch.setenv("INSTAGRAM_SCHEDULER_ENABLED", "false")
    post = {"id": "7e4aa784-75e3-48fc-b366-5ef14466f771", "caption": "scheduled", "media_url": "https://cdn.example.com/ready.jpg", "media_type": "IMAGE"}
    now = publishing._now()
    with publishing._db() as db:
        db.execute("INSERT INTO instagram_posts(id,caption,media_url,media_type,state,scheduled_at,approved_hash,approved_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                   (post["id"], post["caption"], post["media_url"], post["media_type"], "scheduled", (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), publishing._content_hash(post), now, now, now))
    with TestClient(app) as client:
        monkeypatch.setenv("INSTAGRAM_SCHEDULER_ENABLED", "true")
        assert client.get("/api/instagram/scheduler").status_code == 401
        owner_login(client)
        assert client.get("/api/instagram/scheduler").json() == {"configured": True, "paused": False, "active": True}
        pause = client.post("/api/instagram/scheduler/pause", json={}, headers={"Origin": "http://localhost:3000"})
        assert pause.status_code == 200 and pause.json() == {"configured": True, "paused": True, "active": False}
        assert publishing._claim(post["id"], due_only=True) is False
        resume = client.post("/api/instagram/scheduler/resume", json={}, headers={"Origin": "http://localhost:3000"})
        assert resume.status_code == 200 and resume.json() == {"configured": True, "paused": False, "active": True}
        assert publishing._claim(post["id"], due_only=True) is True
        assert publishing._claim(post["id"], due_only=True) is False


def test_scheduler_control_rejects_foreign_origin(monkeypatch, tmp_path):
    configure_publish(monkeypatch, tmp_path)
    with TestClient(app) as client:
        owner_login(client)
        response = client.post("/api/instagram/scheduler/pause", json={}, headers={"Origin": "https://attacker.example"})
        assert response.status_code == 403
