import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.future import select
from app.core.database import async_session
from app.api.auth import get_current_user, User
from app.models.notification_rule import NotificationRule

logger = logging.getLogger("api.notification_rules")

router = APIRouter(prefix="/notification-rules", tags=["Notification Rules"])


class RuleCreate(BaseModel):
    name: str
    repo_pattern: str | None = None
    branch_pattern: str | None = None
    status_filter: str | None = None
    channels: str


class RuleUpdate(BaseModel):
    name: str | None = None
    repo_pattern: str | None = None
    branch_pattern: str | None = None
    status_filter: str | None = None
    channels: str | None = None
    is_active: bool | None = None


@router.get("", summary="List notification rules")
async def list_rules(_: User = Depends(get_current_user)):
    async with async_session() as db:
        result = await db.execute(select(NotificationRule).order_by(NotificationRule.created_at.desc()))
        rules = result.scalars().all()
    return [r.to_dict() for r in rules]


@router.post("", status_code=201, summary="Create notification rule")
async def create_rule(req: RuleCreate, _: User = Depends(get_current_user)):
    async with async_session() as db:
        async with db.begin():
            rule = NotificationRule(
                name=req.name,
                repo_pattern=req.repo_pattern,
                branch_pattern=req.branch_pattern,
                status_filter=req.status_filter,
                channels=req.channels,
            )
            db.add(rule)
            await db.flush()
            return rule.to_dict()


@router.put("/{rule_id}", summary="Update notification rule")
async def update_rule(rule_id: str, req: RuleUpdate, _: User = Depends(get_current_user)):
    async with async_session() as db:
        async with db.begin():
            result = await db.execute(select(NotificationRule).where(NotificationRule.id == rule_id))
            rule = result.scalar_one_or_none()
            if not rule:
                raise HTTPException(404, "Rule not found")
            if req.name is not None:
                rule.name = req.name
            if req.repo_pattern is not None:
                rule.repo_pattern = req.repo_pattern
            if req.branch_pattern is not None:
                rule.branch_pattern = req.branch_pattern
            if req.status_filter is not None:
                rule.status_filter = req.status_filter
            if req.channels is not None:
                rule.channels = req.channels
            if req.is_active is not None:
                rule.is_active = req.is_active
            return rule.to_dict()


@router.delete("/{rule_id}", summary="Delete notification rule")
async def delete_rule(rule_id: str, _: User = Depends(get_current_user)):
    async with async_session() as db:
        async with db.begin():
            result = await db.execute(select(NotificationRule).where(NotificationRule.id == rule_id))
            rule = result.scalar_one_or_none()
            if not rule:
                raise HTTPException(404, "Rule not found")
            await db.delete(rule)
            return {"message": "Rule deleted"}
