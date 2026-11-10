import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.content import ContentRequest, ContentResponse, generate_content
from app.reel_studio import ReelStudioRequest, ReelStudioResponse, generate_reel_studio
from app.instagram_oauth import router as instagram_router
from app.instagram_insights import router as instagram_insights_router
from app.owner_auth import router as owner_auth_router
from app.instagram_publishing import router as instagram_publishing_router, scheduler_enabled, scheduled_publisher_loop


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
    version="0.4.0",
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


@app.post("/api/content/reel-studio", response_model=ReelStudioResponse, tags=["content"])
def content_reel_studio(request: ReelStudioRequest) -> ReelStudioResponse:
    """Create a bilingual, editable shot-by-shot Reel outline using local templates."""
    return generate_reel_studio(request)


@app.get("/healthz", tags=["system"])
def health_check() -> dict[str, str]:
    """Report process health; not a live Instagram check."""
    return {"status": "ok", "stage": "instagram_oauth_scaffold", "instagram": "not_connected"}


@app.post("/api/content/generate", response_model=ContentResponse, tags=["content"])
def content_generate(request: ContentRequest) -> ContentResponse:
    """Generate editable starter ideas, captions, or Reel scripts without paid APIs."""
    return generate_content(request)
