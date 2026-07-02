import logging
import hashlib
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.config import settings
from app.api.webhooks import router as webhooks_router
from app.api.pipeline_runs import router as runs_router
from app.api.stats import router as stats_router
from app.api.audit import router as audit_router
from app.core.database import Base, engine, async_session
from app.services.queue import redis_queue

# Import models so they are registered on Base.metadata
import app.models.pipeline          # noqa: F401
import app.models.audit_event       # noqa: F401
import app.models.api_key           # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


async def _seed_api_key() -> None:
    """If SEED_API_KEY is set and not yet in the DB, insert it on startup."""
    if not settings.SEED_API_KEY:
        return
    from app.models.api_key import ApiKey
    from sqlalchemy.future import select

    key_hash = hashlib.sha256(settings.SEED_API_KEY.encode()).hexdigest()
    async with async_session() as db:
        async with db.begin():
            from sqlalchemy.future import select
            result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
            existing = result.scalar_one_or_none()
            if not existing:
                db.add(ApiKey(name="seed-key", key_hash=key_hash, is_active=True))
                logger.info("Seeded default API key into the database.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_api_key()
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

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus metrics ────────────────────────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# ── Health & Readiness ────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple service health validation endpoint."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "debug_mode": settings.DEBUG,
    }


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness probe – checks DB and Redis connectivity."""
    errors: list[str] = []

    # Check DB
    try:
        async with async_session() as db:
            await db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception as exc:
        errors.append(f"database: {exc}")

    # Check Redis
    try:
        redis_client = await redis_queue.get_redis()
        await redis_client.ping()
    except Exception as exc:
        errors.append(f"redis: {exc}")

    if errors:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail={"status": "not ready", "errors": errors})

    return {"status": "ready"}


# ── API Routers ───────────────────────────────────────────────────────────────
app.include_router(webhooks_router, prefix=settings.API_V1_STR)
app.include_router(runs_router, prefix=settings.API_V1_STR)
app.include_router(stats_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
