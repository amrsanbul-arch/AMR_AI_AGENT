from fastapi import FastAPI

app = FastAPI(
    title="AMR AI – Personal Instagram Manager",
    version="0.1.0",
    description="Initial API scaffold. Instagram is not connected.",
)


@app.get("/healthz", tags=["system"])
def health_check() -> dict[str, str]:
    """Report service process health; this does not test Instagram connectivity."""
    return {"status": "ok", "stage": "scaffold", "instagram": "not_connected"}
