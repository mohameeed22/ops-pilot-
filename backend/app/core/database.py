from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Create database engine with async pg driver
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

# Async session maker
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# SQLAlchemy 2.0 Base class
class Base(DeclarativeBase):
    pass

# FastAPI Dependency for obtaining DB session
async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
