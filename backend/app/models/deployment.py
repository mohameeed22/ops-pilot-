import uuid
from datetime import datetime
from sqlalchemy import String, Text, BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    deployed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    run_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo_name": self.repo_name,
            "environment": self.environment,
            "version": self.version,
            "status": self.status,
            "deployed_by": self.deployed_by,
            "commit_sha": self.commit_sha,
            "branch": self.branch,
            "run_id": self.run_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
