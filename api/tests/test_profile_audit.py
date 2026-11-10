from fastapi.testclient import TestClient
from fastapi import HTTPException

from app import profile_audit
from app.main import app
from app.owner_auth import require_owner

client = TestClient(app)


def test_report_only_exposes_returned_official_fields_and_labels_manual_input():
    report = profile_audit.build_profile_audit(
        {"user_id": "123", "username": "creator", "account_type": "CREATOR", "media_count": 9,
         "biography": "should not be permitted"},
        {"bio": "Food tips — DM me", "niche": "Food", "audience": "home cooks"},
        official_status="available",
    )
    assert report["official_fields"] == {"user_id": "123", "username": "creator", "account_type": "CREATOR", "media_count": 9}
    assert "biography" in report["official_fields_not_returned"]
    assert report["manual_review"]["bio_character_count"] == len("Food tips — DM me")
    assert report["manual_review"]["bio_contains_simple_cta_cue"] is True
    assert report["manual_review"]["bio_contains_manual_niche_text"] is True
    assert next(item for item in report["checks"] if item["key"] == "bio")["source"] == "manual"
    assert "edited" in report["notice"]


def test_missing_context_stays_unreviewed_without_fabricated_account_data():
    report = profile_audit.build_profile_audit(None, {}, official_status="not_connected")
    assert report["status"] == "limited"
    assert report["official_fields"] == {}
    assert report["official_source"] is None
    assert report["manual_review"]["bio_character_count"] is None
    assert report["manual_review"]["bio_contains_simple_cta_cue"] is None
    assert all(item["basis"] != "manual_input" for item in report["review_prompts"])


def test_audit_endpoint_reuses_official_read_only_account_function(monkeypatch):
    app.dependency_overrides[require_owner] = lambda: None
    monkeypatch.setattr(profile_audit.instagram_oauth.Settings, "from_env", lambda: type("S", (), {"configured": lambda self: True})())
    def fake_account():
        return {"provider": "instagram", "user_id": "123", "username": "creator", "account_type": "CREATOR", "media_count": 4}
    monkeypatch.setattr(profile_audit.instagram_oauth, "instagram_account", fake_account)
    response = client.post("/api/profile/audit", json={"bio": "Say hello", "niche": "coffee"})
    assert response.status_code == 200
    result = response.json()
    assert result["official_fields"] == {"user_id": "123", "username": "creator", "account_type": "CREATOR", "media_count": 4}
    assert result["manual_review"]["fields_received"] == ["bio", "niche"]
    assert result["manual_review"]["bio_contains_manual_niche_text"] is False
    app.dependency_overrides.clear()


def test_audit_endpoint_keeps_manual_review_available_when_account_not_connected(monkeypatch):
    app.dependency_overrides[require_owner] = lambda: None
    monkeypatch.setattr(profile_audit.instagram_oauth.Settings, "from_env", lambda: type("S", (), {"configured": lambda self: True})())
    def not_connected():
        raise HTTPException(status_code=409, detail="Instagram is not connected.")
    monkeypatch.setattr(profile_audit.instagram_oauth, "instagram_account", not_connected)
    response = client.post("/api/profile/audit", json={"display_name": "My profile"})
    assert response.status_code == 200
    assert response.json()["official_status"] == "not_connected"
    assert response.json()["official_fields"] == {}
    assert response.json()["manual_review"]["fields_received"] == ["display_name"]
    app.dependency_overrides.clear()


def test_audit_rejects_oversized_manual_fields_before_processing():
    app.dependency_overrides[require_owner] = lambda: None
    response = client.post("/api/profile/audit", json={"bio": "x" * 2001})
    assert response.status_code == 422
    app.dependency_overrides.clear()
