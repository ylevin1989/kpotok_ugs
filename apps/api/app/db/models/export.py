from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import ExportFormat, ExportStatus
from app.db.mixins import CreatedByMixin, OrganizationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Export(UUIDPrimaryKeyMixin, OrganizationScopedMixin, CreatedByMixin, TimestampMixin, Base):
    __tablename__ = 'exports'

    brand_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True),
        ForeignKey('brands.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    content_plan_id: Mapped[UUID | None] = mapped_column(
        SAUUID(as_uuid=True),
        ForeignKey('content_plans.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    format: Mapped[ExportFormat] = mapped_column(
        Enum(ExportFormat, name='export_format', values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        nullable=False,
    )
    status: Mapped[ExportStatus] = mapped_column(
        Enum(ExportStatus, name='export_status', values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        nullable=False,
        default=ExportStatus.PENDING,
        index=True,
    )
    filter_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    file_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
