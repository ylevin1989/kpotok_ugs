from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import GenerationType
from app.db.mixins import OrganizationScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ContentVersion(UUIDPrimaryKeyMixin, OrganizationScopedMixin, TimestampMixin, Base):
    __tablename__ = 'content_versions'
    __table_args__ = (
        UniqueConstraint('content_item_id', 'version_number', name='uq_content_versions_item_version'),
        CheckConstraint('version_number > 0', name='ck_content_versions_version_number_positive'),
    )

    content_item_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True),
        ForeignKey('content_items.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    body_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_type: Mapped[GenerationType] = mapped_column(
        Enum(GenerationType, name='generation_type'),
        nullable=False,
    )
    generated_from_task_id: Mapped[UUID | None] = mapped_column(
        SAUUID(as_uuid=True),
        nullable=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        SAUUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
