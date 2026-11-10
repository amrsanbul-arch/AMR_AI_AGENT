import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.content import ContentRequest, ContentResponse, generate_content
from app.instagram_oauth import router as instagram_router

app = FastAPI(
    title="AMR AI – Personal Instagram Manager",
    version="0.4.0",
    description="Content assistant and optional official Instagram OAuth scaffold. No account is connected by default.",
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
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(instagram_router)


@app.get("/healthz", tags=["system"])
def health_check() -> dict[str, str]:
    """Report process health; not a live Instagram check."""
    return {"status": "ok", "stage": "instagram_oauth_scaffold", "instagram": "not_connected"}


@app.post("/api/content/generate", response_model=ContentResponse, tags=["content"])
def content_generate(request: ContentRequest) -> ContentResponse:
    """Generate editable starter ideas, captions, or Reel scripts without paid APIs."""
    return generate_content(request)
