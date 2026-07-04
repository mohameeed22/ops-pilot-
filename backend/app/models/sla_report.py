import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SLAReport(Base):
    __tablename__ = "sla_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    passed_runs: Mapped[int] = mapped_column(Integer, default=0)
    failed_runs: Mapped[int] = mapped_column(Integer, default=0)
    flaky_runs: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_mttr_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo_name": self.repo_name,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "total_runs": self.total_runs,
            "passed_runs": self.passed_runs,
            "failed_runs": self.failed_runs,
            "flaky_runs": self.flaky_runs,
            "success_rate": self.success_rate,
            "avg_mttr_minutes": self.avg_mttr_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
