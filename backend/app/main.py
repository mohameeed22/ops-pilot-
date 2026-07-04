import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.config import settings
from app.api.webhooks import router as webhooks_router
from app.api.pipeline_runs import router as runs_router
from app.api.stats import router as stats_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.notification_rules import router as notif_rules_router
from app.api.deployments import router as deployments_router
from app.api.rerun import router as rerun_router
from app.api.sla import router as sla_router
from app.core.database import Base, engine, async_session
from app.services.queue import redis_queue

import app.models.pipeline
import app.models.audit_event
import app.models.api_key
import app.models.flaky_test
import app.models.user
import app.models.notification_rule
import app.models.deployment
import app.models.sla_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


async def _seed_admin_user() -> None:
    if not settings.SEED_API_KEY:
        return
    from app.models.user import User
    from sqlalchemy.future import select

    async with async_session() as db:
        async with db.begin():
            result = await db.execute(select(User).where(User.email == "admin@opspilot.com"))
            existing = result.scalar_one_or_none()
            if not existing:
                db.add(User(
                    email="admin@opspilot.com",
                    hashed_password=User.hash_password(settings.SEED_API_KEY),
                    full_name="System Administrator",
                    role="admin"
                ))
                logger.info("Seeded default admin user (admin@opspilot.com) using SEED_API_KEY as password.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_admin_user()
    yield
    await redis_queue.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "debug_mode": settings.DEBUG,
    }


@app.get("/ready", tags=["Health"])
async def readiness_check():
    errors: list[str] = []
    try:
        async with async_session() as db:
            await db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception as exc:
        errors.append(f"database: {exc}")
    try:
        redis_client = await redis_queue.get_redis()
        await redis_client.ping()
    except Exception as exc:
        errors.append(f"redis: {exc}")
    if errors:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail={"status": "not ready", "errors": errors})
    return {"status": "ready"}


app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(webhooks_router, prefix=settings.API_V1_STR)
app.include_router(runs_router, prefix=settings.API_V1_STR)
app.include_router(stats_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(notif_rules_router, prefix=settings.API_V1_STR)
app.include_router(deployments_router, prefix=settings.API_V1_STR)
app.include_router(rerun_router, prefix=settings.API_V1_STR)
app.include_router(sla_router, prefix=settings.API_V1_STR)
