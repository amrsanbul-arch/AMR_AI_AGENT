from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_reel_studio_returns_bilingual_shotlist_with_valid_timing():
    response = client.post("/api/content/reel-studio", json={"topic": "food photography", "audience": "small restaurants", "duration_seconds": 30, "tone": "friendly"})
    assert response.status_code == 200
    result = response.json()
    assert result["generator"] == "free_template"
    assert result["duration_seconds"] == 30
    assert len(result["scenes"]) == 4
    assert result["scenes"][0]["start_seconds"] == 0
    assert result["scenes"][-1]["end_seconds"] == 30
    for previous, current in zip(result["scenes"], result["scenes"][1:]):
        assert previous["end_seconds"] == current["start_seconds"]
    assert all(scene["shot_ar"] and scene["shot_en"] and scene["voiceover_ar"] and scene["voiceover_en"] for scene in result["scenes"])
    assert "food photography" in result["title_en"]
    assert "food photography" in result["voiceover_en"]
    assert "لا تُنشئ صورًا أو فيديو" in result["production_note_ar"]


def test_reel_studio_supports_all_durations():
    expected_scenes = {15: 4, 30: 4, 45: 4}
    for duration, count in expected_scenes.items():
        response = client.post("/api/content/reel-studio", json={"topic": "travel tips", "duration_seconds": duration})
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["scenes"]) == count
        assert payload["scenes"][-1]["end_seconds"] == duration


def test_reel_studio_rejects_invalid_duration_and_blank_topic():
    assert client.post("/api/content/reel-studio", json={"topic": "reels", "duration_seconds": 20}).status_code == 422
    assert client.post("/api/content/reel-studio", json={"topic": "  "}).status_code == 422
