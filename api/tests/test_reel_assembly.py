from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_plan_generates_safe_local_image_only_script():
    response = client.post("/api/content/reel-assembly/plan", json={
        "scenes": [
            {"image_extension": "jpg", "duration_seconds": 4},
            {"image_extension": "webp", "duration_seconds": 6},
        ],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["duration_seconds"] == 10
    assert (data["width"], data["height"], data["fps"]) == (720, 1280, 30)
    assert "assets/scene_01.jpg" in data["script"]
    assert "assets/scene_02.webp" in data["script"]
    assert "concat=n=2:v=1:a=0[outv]" in data["script"]
    assert "-an -t 10" in data["script"]
    assert "Nothing is uploaded or published" in data["note_en"]


def test_plan_adds_optional_looped_audio_and_bounds_runtime():
    response = client.post("/api/content/reel-assembly/plan", json={
        "scenes": [{"image_extension": "png", "duration_seconds": 5}],
        "audio_extension": "mp3",
    })
    assert response.status_code == 200
    assert "assets/soundtrack.mp3" in response.json()["script"]
    assert "-stream_loop -1" in response.json()["script"]
    script = response.json()["script"]
    assert "-map 1:a:0 -c:a aac" in script
    assert script.index("-stream_loop -1 -i") < script.index("-filter_complex")
    assert "-t 5" in response.json()["script"]


def test_plan_rejects_untrusted_extensions_and_invalid_scene_limits():
    bad_extension = client.post("/api/content/reel-assembly/plan", json={
        "scenes": [{"image_extension": "../../etc/passwd", "duration_seconds": 3}],
    })
    too_many = client.post("/api/content/reel-assembly/plan", json={
        "scenes": [{"image_extension": "jpg", "duration_seconds": 1}] * 13,
    })
    too_long = client.post("/api/content/reel-assembly/plan", json={
        "scenes": [{"image_extension": "jpg", "duration_seconds": 60}] * 4,
    })
    assert bad_extension.status_code == 422
    assert too_many.status_code == 422
    assert too_long.status_code == 422
