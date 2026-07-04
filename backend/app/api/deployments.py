import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from app.core.database import async_session
from app.api.auth import get_current_user, User
from app.models.deployment import Deployment

logger = logging.getLogger("api.deployments")

router = APIRouter(prefix="/deployments", tags=["Deployments"])


class DeploymentCreate(BaseModel):
    repo_name: str
    environment: str
    version: str | None = None
    status: str = "pending"
    deployed_by: str | None = None
    commit_sha: str | None = None
    branch: str | None = None
    run_id: int | None = None
    notes: str | None = None


class DeploymentUpdate(BaseModel):
    status: str | None = None
    completed_at: datetime | None = None
    notes: str | None = None
    version: str | None = None


@router.get("", summary="List deployments")
async def list_deployments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repo: str | None = None,
    environment: str | None = None,
    _: User = Depends(get_current_user),
):
    offset = (page - 1) * page_size
    async with async_session() as db:
        query = select(Deployment)
        count_query = select(func.count()).select_from(Deployment)
        if repo:
            query = query.where(Deployment.repo_name == repo)
            count_query = count_query.where(Deployment.repo_name == repo)
        if environment:
            query = query.where(Deployment.environment == environment)
            count_query = count_query.where(Deployment.environment == environment)
        query = query.order_by(Deployment.created_at.desc()).offset(offset).limit(page_size)
        total = (await db.execute(count_query)).scalar_one()
        items = (await db.execute(query)).scalars().all()
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [d.to_dict() for d in items],
    }


@router.post("", status_code=201, summary="Record a deployment")
async def create_deployment(req: DeploymentCreate, _: User = Depends(get_current_user)):
    async with async_session() as db:
        async with db.begin():
            dep = Deployment(**req.model_dump())
            db.add(dep)
            return dep.to_dict()


@router.put("/{deployment_id}", summary="Update deployment")
async def update_deployment(deployment_id: str, req: DeploymentUpdate, _: User = Depends(get_current_user)):
    async with async_session() as db:
        async with db.begin():
            result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
            dep = result.scalar_one_or_none()
            if not dep:
                raise HTTPException(404, "Deployment not found")
            update_data = req.model_dump(exclude_unset=True)
            for key, val in update_data.items():
                setattr(dep, key, val)
            return dep.to_dict()


@router.get("/stats", summary="Deployment statistics")
async def deployment_stats(_: User = Depends(get_current_user)):
    async with async_session() as db:
        total = (await db.execute(select(func.count(Deployment.id)))).scalar_one()
        by_env = await db.execute(
            select(Deployment.environment, func.count(Deployment.id).label("count"))
            .group_by(Deployment.environment)
        )
        env_counts = {row.environment: row.count for row in by_env}
        recent = await db.execute(
            select(Deployment).order_by(Deployment.created_at.desc()).limit(10)
        )
        recent_deps = [d.to_dict() for d in recent.scalars().all()]
    return {
        "total": total,
        "by_environment": env_counts,
        "recent": recent_deps,
    }
