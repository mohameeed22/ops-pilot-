from fastapi import FastAPI
from app.core.config import settings
from app.api.webhooks import router as webhooks_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

@app.get("/health", tags=["Health"])
async def health_check():
    """Simple service health validation endpoint."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "debug_mode": settings.DEBUG,
    }

# Register the GitHub webhook router under the V1 API prefix
app.include_router(webhooks_router, prefix=settings.API_V1_STR)
