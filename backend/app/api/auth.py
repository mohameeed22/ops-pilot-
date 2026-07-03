"""
Authentication API – JWT-based login & user management.

Endpoints:
  POST /api/v1/auth/register  - Create a new user (admin only)
  POST /api/v1/auth/login     - Obtain a JWT access token
  GET  /api/v1/auth/me        - Get current authenticated user info
  GET  /api/v1/auth/users     - List all users (admin only)
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.future import select
import jwt

from app.core.config import settings
from app.core.database import async_session
from app.models.user import User

logger = logging.getLogger("auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Pydantic schemas ─────────────────────────────────────────────────────────
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    role: str = "viewer"


# ── Token helpers ─────────────────────────────────────────────────────────────
def _create_token(user_id: str, email: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "email": email, "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Dependency: validate JWT and return the associated User."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_error
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.PyJWTError:
        raise credentials_error

    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
        user = result.scalar_one_or_none()

    if not user:
        raise credentials_error
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/login", response_model=LoginResponse, summary="Login and obtain JWT token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Validates email/password and returns a signed JWT access token."""
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == form_data.username))
        user = result.scalar_one_or_none()

    if not user or not user.verify_password(form_data.password) or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = _create_token(user.id, user.email, user.role)
    logger.info(f"User {user.email} logged in successfully.")
    return LoginResponse(access_token=token, user=user.to_dict())


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register(req: RegisterRequest, _: User = Depends(require_admin)):
    """Creates a new user account. Requires admin JWT."""
    async with async_session() as db:
        async with db.begin():
            existing = await db.execute(select(User).where(User.email == req.email))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Email already registered")
            new_user = User(
                email=req.email,
                hashed_password=User.hash_password(req.password),
                full_name=req.full_name,
                role=req.role,
            )
            db.add(new_user)
    return {"message": "User created successfully", "email": req.email}


@router.get("/me", summary="Get current user profile")
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently authenticated user."""
    return current_user.to_dict()


@router.get("/users", summary="List all users (admin only)")
async def list_users(_: User = Depends(require_admin)):
    """Returns all registered users. Admin only."""
    async with async_session() as db:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        users = result.scalars().all()
    return [u.to_dict() for u in users]
