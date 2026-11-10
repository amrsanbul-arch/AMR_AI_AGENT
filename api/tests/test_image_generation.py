import base64

from fastapi.testclient import TestClient

from app import image_generation
from app.main import app
from app.owner_auth import hash_owner_password

client = TestClient(app)


def _configure_auth_and_comfyui(monkeypatch):
    monkeypatch.setenv("IMAGE_GENERATOR", "comfyui")
    monkeypatch.setenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
    monkeypatch.setenv("COMFYUI_CHECKPOINT", "sd_xl_base_1.0.safetensors")
    monkeypatch.setenv("AMR_OWNER_PASSWORD_HASH", hash_owner_password("test-image-password-123"))
    monkeypatch.setenv("AMR_SESSION_SECRET", "test-only-session-secret-that-is-at-least-32-bytes")
    monkeypatch.setenv("APP_ENV", "development")


def test_prompt_only_is_default_and_endpoint_returns_copyable_prompt(monkeypatch):
    monkeypatch.delenv("IMAGE_GENERATOR", raising=False)
    monkeypatch.setenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
    status = client.get("/api/content/image-provider")
    assert status.status_code == 200
    assert status.json() == {"generator": "prompt_only", "configured": False}

    response = client.post("/api/content/image", json={"prompt": "Vertical food photography, warm daylight"})
    assert response.status_code == 200
    assert response.json()["generator"] == "prompt_only"
    assert response.json()["image_data_url"] is None
    assert "no image was generated" in response.json()["notice"]
    assert response.json()["prompt"] == "Vertical food photography, warm daylight"


def test_public_comfyui_host_and_unsafe_checkpoint_are_not_accepted(monkeypatch):
    monkeypatch.setenv("IMAGE_GENERATOR", "comfyui")
    monkeypatch.setenv("COMFYUI_BASE_URL", "https://example.com")
    monkeypatch.setenv("COMFYUI_CHECKPOINT", "../../private.safetensors")
    assert image_generation.image_provider_status() == {"generator": "prompt_only", "configured": False}


def test_real_local_generation_requires_owner_login(monkeypatch):
    _configure_auth_and_comfyui(monkeypatch)
    client.cookies.clear()
    response = client.post("/api/content/image", json={"prompt": "A bright editorial portrait"})
    assert response.status_code == 401


def test_comfyui_image_result_is_returned_as_png_data_url(monkeypatch):
    _configure_auth_and_comfyui(monkeypatch)
    login = client.post("/api/auth/login", json={"password": "test-image-password-123"})
    assert login.status_code == 200

    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l1sAAAAASUVORK5CYII=")

    class FakeResponse:
        def __init__(self, body, content=b""):
            self._body = body
            self.content = content

        def raise_for_status(self):
            return None

        def json(self):
            return self._body

    class FakeResponseStream(FakeResponse):
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def aiter_bytes(self):
            yield self.content

    class FakeClient:
        def __init__(self, **_kwargs):
            self.polls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, json):
            assert url == "http://127.0.0.1:8188/prompt"
            workflow = json["prompt"]
            assert workflow["4"]["inputs"]["batch_size"] == 1
            assert workflow["4"]["inputs"]["height"] == 1024
            assert workflow["5"]["inputs"]["steps"] == 20
            return FakeResponse({"prompt_id": "job-id_1234"})

        async def get(self, url, params=None):
            if url.endswith("/history/job-id_1234"):
                self.polls += 1
                outputs = {"7": {"images": [{"filename": "AMR_AI_00001_.png", "subfolder": "", "type": "output"}]}} if self.polls > 1 else {}
                return FakeResponse({"job-id_1234": {"outputs": outputs}})
            raise AssertionError("image body should be streamed")

        def stream(self, method, url, params=None):
            assert method == "GET"
            assert url.endswith("/view")
            assert params["filename"] == "AMR_AI_00001_.png"
            return FakeResponseStream({}, png)

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(image_generation.asyncio, "sleep", no_wait)
    monkeypatch.setattr(image_generation.httpx, "AsyncClient", FakeClient)
    response = client.post("/api/content/image", json={"prompt": "Vertical image, handmade ceramic cup, soft daylight"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["generator"] == "comfyui"
    assert payload["image_data_url"].startswith("data:image/png;base64,")
    assert "local ComfyUI" in payload["notice"]


def test_image_prompt_rejects_blank_or_oversized_input():
    assert client.post("/api/content/image", json={"prompt": "  "}).status_code == 422
    assert client.post("/api/content/image", json={"prompt": "x" * 1601}).status_code == 422
