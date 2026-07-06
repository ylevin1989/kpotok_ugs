from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import OrganizationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class QualityCheck(UUIDPrimaryKeyMixin, OrganizationScopedMixin, TimestampMixin, Base):
    __tablename__ = 'quality_checks'
    __table_args__ = (
        CheckConstraint('score >= 0 AND score <= 100', name='ck_quality_checks_score_range'),
        CheckConstraint('threshold >= 0 AND threshold <= 100', name='ck_quality_checks_threshold_range'),
    )

    brand_id: Mapped[UUID] = mapped_column(ForeignKey('brands.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), nullable=True, index=True)
    content_item_id: Mapped[UUID] = mapped_column(ForeignKey('content_items.id', ondelete='CASCADE'), nullable=False, index=True)
    content_version_id: Mapped[UUID] = mapped_column(ForeignKey('content_versions.id', ondelete='CASCADE'), nullable=False, index=True)
    ticket_id: Mapped[UUID | None] = mapped_column(ForeignKey('tickets.id', ondelete='SET NULL'), nullable=True, index=True)
    score: Mapped[int] = mapped_column(nullable=False)
    threshold: Mapped[int] = mapped_column(nullable=False, default=80)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='needs_revision', index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    checks_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    issues_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recommendations_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    generated_from_task_id: Mapped[UUID | None] = mapped_column(SAUUID(as_uuid=True), nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
