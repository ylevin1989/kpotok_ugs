import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContentItem(Base):
    __tablename__ = 'content_items'
    __table_args__ = (
        CheckConstraint("scope != 'product' OR product_id IS NOT NULL", name='ck_content_items_product_scope_requires_product_id'),
        CheckConstraint('quality_score >= 0 AND quality_score <= 100', name='ck_content_items_quality_score_range'),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('brands.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), nullable=True, index=True)
    content_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('content_plans.id', ondelete='CASCADE'), nullable=False, index=True)
    audience_segment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('audience_segments.id', ondelete='CASCADE'), nullable=True, index=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default='brand')
    platform: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='draft')
    quality_score: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
