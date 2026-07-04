import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from app.core.database import async_session
from app.api.auth import get_current_user, User
from app.models.pipeline import PipelineRun

logger = logging.getLogger("api.stats")

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("", summary="Get aggregate pipeline statistics")
async def get_stats(_: User = Depends(get_current_user)):
    async with async_session() as db:
        count_result = await db.execute(
            select(PipelineRun.status, func.count(PipelineRun.id).label("count"))
            .group_by(PipelineRun.status)
        )
        status_counts = {row.status: row.count for row in count_result}

        total = sum(status_counts.values())
        counts = {
            "total": total,
            "pending": status_counts.get("pending", 0),
            "processing": status_counts.get("processing", 0),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
        }

        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        trend_result = await db.execute(
            select(
                func.date(PipelineRun.created_at).label("day"),
                PipelineRun.status,
                func.count(PipelineRun.id).label("count"),
            )
            .where(PipelineRun.created_at >= seven_days_ago)
            .group_by(func.date(PipelineRun.created_at), PipelineRun.status)
            .order_by(func.date(PipelineRun.created_at))
        )
        trend_rows = trend_result.all()

        trend_map: dict[str, dict] = {}
        for row in trend_rows:
            day_str = str(row.day)
            if day_str not in trend_map:
                trend_map[day_str] = {"date": day_str, "completed": 0, "failed": 0, "pending": 0}
            if row.status in trend_map[day_str]:
                trend_map[day_str][row.status] = row.count

        trend = list(trend_map.values())

        top_repos_result = await db.execute(
            select(PipelineRun.repo_name, func.count(PipelineRun.id).label("failures"))
            .where(PipelineRun.status == "failed")
            .group_by(PipelineRun.repo_name)
            .order_by(func.count(PipelineRun.id).desc())
            .limit(5)
        )
        top_failing_repos = [
            {"repo": row.repo_name, "failures": row.failures}
            for row in top_repos_result
        ]

        flaky_count = (
            await db.execute(
                select(func.count(PipelineRun.id)).where(PipelineRun.is_flaky.is_(True))
            )
        ).scalar_one()

        mttr_result = await db.execute(
            select(func.avg(PipelineRun.mttr_minutes)).where(PipelineRun.mttr_minutes.isnot(None))
        )
        avg_mttr = round(mttr_result.scalar_one() or 0, 1)

    return {
        "counts": counts,
        "trend": trend,
        "top_failing_repos": top_failing_repos,
        "flaky_count": flaky_count,
        "avg_mttr_minutes": avg_mttr,
    }
