"""
Pipeline Runs REST API.

Endpoints:
  GET /api/v1/runs           - paginated list of pipeline runs
  GET /api/v1/runs/{run_id}  - single run detail
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from app.core.database import async_session
from app.api.auth import get_current_user, User
from app.models.pipeline import PipelineRun

logger = logging.getLogger("api.runs")

router = APIRouter(prefix="/runs", tags=["Pipeline Runs"])


@router.get("", summary="List pipeline runs")
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by status (pending, processing, completed, failed)"),
    repo: str | None = Query(None, description="Filter by repository name (partial match)"),
    _: User = Depends(get_current_user),
):
    """Returns a paginated list of pipeline runs, newest first."""
    offset = (page - 1) * page_size

    async with async_session() as db:
        query = select(PipelineRun)
        count_query = select(func.count()).select_from(PipelineRun)

        if status:
            query = query.where(PipelineRun.status == status)
            count_query = count_query.where(PipelineRun.status == status)
        if repo:
            like_expr = f"%{repo}%"
            query = query.where(PipelineRun.repo_name.ilike(like_expr))
            count_query = count_query.where(PipelineRun.repo_name.ilike(like_expr))

        query = query.order_by(PipelineRun.created_at.desc()).offset(offset).limit(page_size)

        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        runs_result = await db.execute(query)
        runs = runs_result.scalars().all()

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "items": [r.to_dict() for r in runs],
    }


@router.get("/flaky", summary="Get list of flaky tests")
async def list_flaky_tests(
    _: User = Depends(get_current_user),
):
    """Returns a list of all identified flaky tests."""
    from app.models.flaky_test import FlakyTest
    async with async_session() as db:
        stmt = select(FlakyTest).order_by(FlakyTest.failure_count.desc())
        result = await db.execute(stmt)
        flaky_tests = result.scalars().all()
    return [t.to_dict() for t in flaky_tests]


@router.get("/{run_id}", summary="Get a single pipeline run by GitHub run ID")
async def get_run(
    run_id: int,
    _: User = Depends(get_current_user),
):
    """Returns full detail for a single pipeline run."""
    async with async_session() as db:
        stmt = select(PipelineRun).where(PipelineRun.run_id == run_id)
        result = await db.execute(stmt)
        run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")

    return run.to_dict()
