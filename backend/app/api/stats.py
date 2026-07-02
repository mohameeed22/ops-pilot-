"""
Stats API – aggregate counts and recent trend for the dashboard.
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, case
from app.core.database import async_session
from app.core.security import require_api_key
from app.models.pipeline import PipelineRun

logger = logging.getLogger("api.stats")

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("", summary="Get aggregate pipeline statistics")
async def get_stats(_: object = Depends(require_api_key)):
    """
    Returns:
    - overall counts by status
    - counts for the last 7 days (trend data for the chart)
    - top failing repositories
    """
    async with async_session() as db:
        # --- Overall counts by status ---
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

        # --- Daily trend for the last 7 days ---
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

        # Build a day-keyed dict for the chart
        trend_map: dict[str, dict] = {}
        for row in trend_rows:
            day_str = str(row.day)
            if day_str not in trend_map:
                trend_map[day_str] = {"date": day_str, "completed": 0, "failed": 0, "pending": 0}
            if row.status in trend_map[day_str]:
                trend_map[day_str][row.status] = row.count

        trend = list(trend_map.values())

        # --- Top 5 failing repositories ---
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

    return {
        "counts": counts,
        "trend": trend,
        "top_failing_repos": top_failing_repos,
    }
