import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    brief_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("briefs.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    worker_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    output_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    output_artifact_key: Mapped[str | None] = mapped_column(Text(), nullable=True)
    output_artifact_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    output_artifact_content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_artifact_size_bytes: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    output_artifact_etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    execution_profile: Mapped[str] = mapped_column(String(64), nullable=False, default='general_content')
    internal_role_plan_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    execution_trace_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    last_stage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
