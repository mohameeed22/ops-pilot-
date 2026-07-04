import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import async_session
from app.api.auth import get_current_user, User
from app.models.pipeline import PipelineRun
from app.services.github_app import github_app_service

logger = logging.getLogger("api.rerun")

router = APIRouter(prefix="/rerun", tags=["Rerun"])


@router.post("/{run_id}", summary="Rerun a failed pipeline")
async def rerun_pipeline(run_id: int, _: User = Depends(get_current_user)):
    async with async_session() as db:
        async with db.begin():
            result = await db.execute(select(PipelineRun).where(PipelineRun.run_id == run_id))
            run = result.scalar_one_or_none()
            if not run:
                raise HTTPException(404, "Pipeline run not found")
            if run.rerun_count >= settings.MAX_RERUNS_PER_RUN:
                raise HTTPException(400, f"Max reruns ({settings.MAX_RERUNS_PER_RUN}) reached for this run")
            if run.provider != "github":
                raise HTTPException(400, f"Rerun not supported for provider: {run.provider}")

            run.rerun_count += 1
            run.last_rerun_at = datetime.utcnow()
            run.status = "pending"

    try:
        token = await github_app_service.get_installation_access_token(run.installation_id)
        url = f"https://api.github.com/repos/{run.repo_name}/actions/runs/{run_id}/rerun"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers)
            resp.raise_for_status()
        logger.info(f"Rerun triggered for run {run_id}")
        return {"message": f"Rerun triggered for run {run_id}", "rerun_count": run.rerun_count}
    except Exception as e:
        logger.error(f"Failed to rerun run {run_id}: {e}")
        raise HTTPException(500, f"Failed to rerun: {e}")


@router.get("/flaky/auto-rerun", summary="Auto-rerun known flaky failures")
async def auto_rerun_flaky(_: User = Depends(get_current_user)):
    if not settings.AUTO_RERUN_FLAKY:
        return {"message": "Auto-rerun is disabled (set AUTO_RERUN_FLAKY=True)", "rerun_count": 0}

    async with async_session() as db:
        result = await db.execute(
            select(PipelineRun).where(
                PipelineRun.is_flaky.is_(True),
                PipelineRun.status == "failed",
                PipelineRun.auto_rerun.is_(False),
                PipelineRun.provider == "github",
                PipelineRun.rerun_count < settings.MAX_RERUNS_PER_RUN,
            )
        )
        flaky_runs = result.scalars().all()

    count = 0
    for run in flaky_runs:
        try:
            token = await github_app_service.get_installation_access_token(run.installation_id)
            url = f"https://api.github.com/repos/{run.repo_name}/actions/runs/{run.run_id}/rerun"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=headers)
                resp.raise_for_status()

            async with async_session() as db2:
                async with db2.begin():
                    r = await db2.execute(select(PipelineRun).where(PipelineRun.run_id == run.run_id))
                    db_run = r.scalar_one_or_none()
                    if db_run:
                        db_run.rerun_count += 1
                        db_run.last_rerun_at = datetime.utcnow()
                        db_run.auto_rerun = True
                        db_run.status = "pending"
            count += 1
            logger.info(f"Auto-rerun triggered for flaky run {run.run_id}")
        except Exception as e:
            logger.error(f"Auto-rerun failed for run {run.run_id}: {e}")

    return {"message": f"Auto-rerun triggered for {count} flaky runs", "rerun_count": count}
