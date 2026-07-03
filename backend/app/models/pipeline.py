import uuid
from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    run_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    installation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)

    # GitHub context
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    run_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    workflow_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Parsed error fields (nullable in case of success or unparseable logs)
    error_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    step_log_file: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # LLM-generated incident summary
    llm_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Flaky tracking
    is_flaky: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo_name": self.repo_name,
            "run_id": self.run_id,
            "installation_id": self.installation_id,
            "status": self.status,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "run_url": self.run_url,
            "workflow_name": self.workflow_name,
            "error_language": self.error_language,
            "error_filename": self.error_filename,
            "error_line_number": self.error_line_number,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "error_traceback": self.error_traceback,
            "step_log_file": self.step_log_file,
            "llm_summary": self.llm_summary,
            "is_flaky": self.is_flaky,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

