"""
API Key authentication dependency and utilities.

Usage:
  from app.core.security import require_api_key

  @router.get("/protected")
  async def endpoint(api_key: ApiKey = Depends(require_api_key)):
      ...
"""
import logging
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.future import select
from app.core.database import async_session
from app.models.api_key import ApiKey

logger = logging.getLogger("security")

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(raw_key: str | None = Security(_api_key_header)) -> ApiKey:
    """FastAPI dependency – validates the X-API-Key header against the DB."""
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is missing",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_hash = ApiKey.hash_key(raw_key)
    async with async_session() as db:
        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        result = await db.execute(stmt)
        api_key = result.scalar_one_or_none()

    if not api_key:
        logger.warning("Invalid or inactive API key attempted.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    return api_key
