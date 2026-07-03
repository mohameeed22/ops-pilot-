import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class FlakyTest(Base):
    __tablename__ = "flaky_tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    error_signature: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_flaky: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo_name": self.repo_name,
            "workflow_name": self.workflow_name,
            "error_signature": self.error_signature,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "is_flaky": self.is_flaky,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
