from __future__ import annotations

import asyncio
import base64
import ipaddress
import os
import re
import secrets
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator

from app.owner_auth import _auth_configured, require_owner

router = APIRouter(prefix="/api/content", tags=["content"])
_ALLOWED_HOSTS = {"localhost", "comfyui", "host.docker.internal"}
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,119}\.(?:safetensors|ckpt|pt)$", re.IGNORECASE)
_PROMPT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
_MAX_PNG_BYTES = 5 * 1024 * 1024


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=1600)

    @field_validator("prompt")
    @classmethod
    def clean_prompt(cls, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if len(cleaned) < 2:
            raise ValueError("prompt must contain at least two non-space characters")
        return cleaned


class ImageResponse(BaseModel):
    generator: str
    prompt: str
    image_data_url: str | None = None
    notice: str


def _comfy_url() -> str | None:
    raw = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188").strip().rstrip("/")
    try:
        parsed = urlsplit(raw)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            return None
        host = parsed.hostname.lower()
        if host not in _ALLOWED_HOSTS:
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                return None
            if not (address.is_loopback or address.is_private or address.is_link_local):
                return None
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return None
        return raw
    except ValueError:
        return None


def image_provider_status() -> dict[str, object]:
    selected = os.getenv("IMAGE_GENERATOR", "prompt_only").strip().lower()
    checkpoint = os.getenv("COMFYUI_CHECKPOINT", "sd_xl_base_1.0.safetensors").strip()
    configured = (
        selected == "comfyui"
        and _comfy_url() is not None
        and bool(_MODEL_RE.fullmatch(checkpoint))
        and _auth_configured()
    )
    return {"generator": "comfyui" if configured else "prompt_only", "configured": configured}


def require_image_access(request: Request) -> None:
    # Prompt-only output is safe to provide publicly. Real local inference requires owner auth.
    if image_provider_status()["configured"]:
        require_owner(request)


def _workflow(prompt: str, checkpoint: str) -> dict[str, object]:
    """Fixed, bounded ComfyUI txt2img graph; users cannot submit arbitrary workflows."""
    seed = secrets.randbelow(2**32)
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "text, watermark, logo, low quality, blurry", "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 1024, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 20, "cfg": 6.5, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "AMR_AI", "images": ["6", 0]}},
    }


def _prompt_only(prompt: str, notice: str) -> ImageResponse:
    return ImageResponse(generator="prompt_only", prompt=prompt, notice=notice)


async def generate_image(request: ImageRequest) -> ImageResponse:
    status = image_provider_status()
    if status["generator"] != "comfyui":
        return _prompt_only(
            request.prompt,
            "Image generation is not configured. This is a ready-to-copy prompt; no image was generated.",
        )

    base_url = _comfy_url()
    checkpoint = os.getenv("COMFYUI_CHECKPOINT", "sd_xl_base_1.0.safetensors").strip()
    if not base_url or not _MODEL_RE.fullmatch(checkpoint):
        return _prompt_only(request.prompt, "ComfyUI settings are invalid; no image was generated. The prompt is ready to copy.")

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=3.0), trust_env=False, follow_redirects=False
        ) as client:
            queued = await client.post(f"{base_url}/prompt", json={"prompt": _workflow(request.prompt, checkpoint)})
            queued.raise_for_status()
            prompt_id = queued.json().get("prompt_id")
            if not isinstance(prompt_id, str) or not _PROMPT_ID_RE.fullmatch(prompt_id):
                return _prompt_only(request.prompt, "ComfyUI did not return a usable job receipt; no image is available here. The prompt is ready to copy.")

            deadline = asyncio.get_running_loop().time() + 120
            images: list[dict[str, str]] = []
            while asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(1)
                history_response = await client.get(f"{base_url}/history/{prompt_id}")
                history_response.raise_for_status()
                history = history_response.json()
                job = history.get(prompt_id) if isinstance(history, dict) else None
                outputs = job.get("outputs", {}) if isinstance(job, dict) else {}
                for node in outputs.values() if isinstance(outputs, dict) else []:
                    found = node.get("images", []) if isinstance(node, dict) else []
                    if isinstance(found, list):
                        images.extend(item for item in found if isinstance(item, dict))
                if images:
                    break
            if not images:
                return _prompt_only(request.prompt, "The local image job did not finish before the wait limit; no image is available here. The prompt is ready to copy.")

            image = images[0]
            filename = image.get("filename", "")
            subfolder = image.get("subfolder", "")
            image_type = image.get("type", "output")
            if (
                not isinstance(filename, str)
                or not filename.lower().endswith(".png")
                or filename in {".", ".."}
                or "/" in filename
                or "\\" in filename
                or not isinstance(subfolder, str)
                or any(part in {".", ".."} for part in subfolder.split("/"))
                or image_type not in {"output", "temp"}
            ):
                return _prompt_only(request.prompt, "ComfyUI returned an unsupported image reference; no image is shown. The prompt is ready to copy.")
            image_bytes = bytearray()
            async with client.stream(
                "GET", f"{base_url}/view",
                params={"filename": filename, "subfolder": subfolder, "type": image_type},
            ) as image_response:
                image_response.raise_for_status()
                async for chunk in image_response.aiter_bytes():
                    if len(image_bytes) + len(chunk) > _MAX_PNG_BYTES:
                        return _prompt_only(request.prompt, "The local result exceeded the 5MB image limit; no image is shown. The prompt is ready to copy.")
                    image_bytes.extend(chunk)
            if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                return _prompt_only(request.prompt, "The local result was not a supported PNG; no image is shown. The prompt is ready to copy.")
            data_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")
            return ImageResponse(generator="comfyui", prompt=request.prompt, image_data_url=data_url, notice="Generated by your configured local ComfyUI server; review before use.")
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
        return _prompt_only(request.prompt, "The local image service did not return a usable result; the image is unavailable here. The prompt is ready to copy.")


@router.get("/image-provider")
def content_image_provider() -> dict[str, object]:
    """Expose capability state, never the local service address or model files."""
    return image_provider_status()


@router.post("/image", response_model=ImageResponse, dependencies=[Depends(require_image_access)])
async def content_image(request: ImageRequest) -> ImageResponse:
    return await generate_image(request)
