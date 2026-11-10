import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.content import ContentRequest, ContentResponse
from app.reel_studio import ReelStudioRequest, ReelStudioResponse
from app.content_generation import generate_content_with_provider, generate_reel_with_provider
from app.local_ai import provider_status
from app.image_generation import router as image_router
from app.owner_auth import require_owner
from app.instagram_oauth import router as instagram_router
from app.instagram_insights import router as instagram_insights_router
from app.owner_auth import router as owner_auth_router
from app.instagram_publishing import router as instagram_publishing_router, scheduler_enabled, scheduled_publisher_loop
from app.trends import router as trends_router
from app.strategy import router as strategy_router
from app.profile_audit import router as profile_audit_router


@asynccontextmanager
async def lifespan(_app):
    scheduler = asyncio.create_task(scheduled_publisher_loop()) if scheduler_enabled() else None
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.cancel()
            try:
                await scheduler
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="AMR AI – Personal Instagram Manager",
    version="0.5.0",
    description="Content assistant and optional official Instagram OAuth scaffold. No account is connected by default.",
    lifespan=lifespan,
)

web_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("WEB_ORIGIN", "http://localhost:3000").split(",")
    if origin.strip()
]
if "WEB_ORIGIN" not in os.environ:
    web_origins.append("http://127.0.0.1:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=web_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(owner_auth_router)
app.include_router(instagram_router)
app.include_router(instagram_insights_router)
app.include_router(instagram_publishing_router)
app.include_router(image_router)
app.include_router(trends_router)
app.include_router(strategy_router)
app.include_router(profile_audit_router)


def require_content_access(request: Request) -> None:
    # Template generation remains usable without sign-in; local-model requests require owner auth.
    if provider_status()["generator"] == "ollama":
        require_owner(request)


@app.post("/api/content/reel-studio", response_model=ReelStudioResponse, tags=["content"], dependencies=[Depends(require_content_access)])
async def content_reel_studio(request: ReelStudioRequest) -> ReelStudioResponse:
    """Create a bilingual Reel outline with local templates or configured local Ollama."""
    return await generate_reel_with_provider(request)


@app.get("/healthz", tags=["system"])
def health_check() -> dict[str, str]:
    """Report process health; not a live Instagram check."""
    return {"status": "ok", "stage": "amr_ai_api", "instagram": "not_connected"}


@app.post("/api/content/generate", response_model=ContentResponse, tags=["content"], dependencies=[Depends(require_content_access)])
async def content_generate(request: ContentRequest) -> ContentResponse:
    """Generate drafts using optional server-configured local Ollama or free templates."""
    return await generate_content_with_provider(request)


@app.get("/api/content/provider", tags=["content"])
def content_provider_status() -> dict[str, object]:
    """Report the selected generator and model name only; never reveal endpoint or secrets."""
    return provider_status()
