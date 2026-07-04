import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from app.core.database import async_session
from app.api.auth import get_current_user, User
from app.models.pipeline import PipelineRun

logger = logging.getLogger("api.sla")

router = APIRouter(prefix="/sla", tags=["SLA"])


@router.get("", summary="SLA/MTTR dashboard data")
async def get_sla_data(
    days: int = Query(7, ge=1, le=90),
    repo: str | None = None,
    _: User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)

    async with async_session() as db:
        query = select(PipelineRun).where(PipelineRun.created_at >= since)
        count_query = select(func.count()).select_from(PipelineRun).where(PipelineRun.created_at >= since)
        if repo:
            query = query.where(PipelineRun.repo_name == repo)
            count_query = count_query.where(PipelineRun.repo_name == repo)

        all_runs = (await db.execute(query)).scalars().all()

    total = len(all_runs)
    passed = sum(1 for r in all_runs if r.status == "completed")
    failed = sum(1 for r in all_runs if r.status == "failed")
    flaky = sum(1 for r in all_runs if r.is_flaky)
    pending = sum(1 for r in all_runs if r.status in ("pending", "processing"))
    success_rate = round((passed / total * 100), 1) if total > 0 else 0.0

    mttr_values = [r.mttr_minutes for r in all_runs if r.mttr_minutes is not None]
    avg_mttr = round(sum(mttr_values) / len(mttr_values), 1) if mttr_values else None

    by_repo = {}
    for r in all_runs:
        if r.repo_name not in by_repo:
            by_repo[r.repo_name] = {"total": 0, "passed": 0, "failed": 0, "flaky": 0}
        by_repo[r.repo_name]["total"] += 1
        if r.status == "completed":
            by_repo[r.repo_name]["passed"] += 1
        elif r.status == "failed":
            by_repo[r.repo_name]["failed"] += 1
        if r.is_flaky:
            by_repo[r.repo_name]["flaky"] += 1

    repo_breakdown = [
        {
            "repo": name,
            **vals,
            "success_rate": round((vals["passed"] / vals["total"] * 100), 1) if vals["total"] > 0 else 0.0,
        }
        for name, vals in sorted(by_repo.items(), key=lambda x: x[1]["total"], reverse=True)
    ]

    return {
        "period_days": days,
        "total_runs": total,
        "passed": passed,
        "failed": failed,
        "flaky": flaky,
        "pending": pending,
        "success_rate": success_rate,
        "avg_mttr_minutes": avg_mttr,
        "repo_breakdown": repo_breakdown,
    }
