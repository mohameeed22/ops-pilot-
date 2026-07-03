"""
Audit Log API – paginated system event log.
"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from app.core.database import async_session
from app.api.auth import get_current_user, User
from app.models.audit_event import AuditEvent

logger = logging.getLogger("api.audit")

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", summary="Paginated audit event log")
async def list_audit_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: str | None = Query(None, description="Filter by event type"),
    _: User = Depends(get_current_user),
):
    """Returns a paginated audit log of all system events, newest first."""
    offset = (page - 1) * page_size

    async with async_session() as db:
        query = select(AuditEvent)
        count_query = select(func.count()).select_from(AuditEvent)

        if event_type:
            query = query.where(AuditEvent.event_type == event_type)
            count_query = count_query.where(AuditEvent.event_type == event_type)

        query = query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(page_size)

        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        events_result = await db.execute(query)
        events = events_result.scalars().all()

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "items": [e.to_dict() for e in events],
    }
