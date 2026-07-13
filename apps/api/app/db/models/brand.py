import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BrandStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_brands_org_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[BrandStatus] = mapped_column(
        SqlEnum(
            BrandStatus,
            name="brand_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=BrandStatus.ACTIVE,
        nullable=False,
    )
    dna_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    positioning: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone_of_voice: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    mission: Mapped[str | None] = mapped_column(Text, nullable=True)
    values: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    forbidden_claims: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    allowed_claims: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    competitors: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    good_examples: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    bad_examples: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
