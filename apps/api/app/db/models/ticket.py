from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import OrganizationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Ticket(UUIDPrimaryKeyMixin, OrganizationScopedMixin, TimestampMixin, Base):
    __tablename__ = 'tickets'

    brand_id: Mapped[UUID] = mapped_column(ForeignKey('brands.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), nullable=True, index=True)
    content_item_id: Mapped[UUID] = mapped_column(ForeignKey('content_items.id', ondelete='CASCADE'), nullable=False, index=True)
    content_version_id: Mapped[UUID | None] = mapped_column(ForeignKey('content_versions.id', ondelete='SET NULL'), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='open', index=True)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default='normal', index=True)
    assigned_agent_role: Mapped[str] = mapped_column(String(64), nullable=False, default='content_creator', index=True)
    created_by_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
