import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.content import ContentRequest, ContentResponse, generate_content

app = FastAPI(
    title="AMR AI – Personal Instagram Manager",
    version="0.3.0",
    description="Content assistant starter. Instagram is not connected.",
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


@app.get("/healthz", tags=["system"])
def health_check() -> dict[str, str]:
    """Report service process health; this does not test Instagram connectivity."""
    return {"status": "ok", "stage": "content_assistant", "instagram": "not_connected"}


@app.post("/api/content/generate", response_model=ContentResponse, tags=["content"])
def content_generate(request: ContentRequest) -> ContentResponse:
    """Generate editable starter ideas, captions, or Reel scripts without paid APIs."""
    return generate_content(request)
