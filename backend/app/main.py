from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.api.webhooks import router as webhooks_router
from app.core.database import Base, engine
from app.services.queue import redis_queue

# Import models to ensure they are registered on Base.metadata
import app.models.pipeline 

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: Close Redis connection
    await redis_queue.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
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
