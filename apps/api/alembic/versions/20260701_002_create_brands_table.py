"""create brands table

Revision ID: 20260701_002
Revises: 20260701_001
Create Date: 2026-07-01 12:45:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260701_002"
down_revision: str | None = "20260701_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_brands_org_slug"),
    )
    op.create_index("ix_brands_organization_id", "brands", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_brands_organization_id", table_name="brands")
    op.drop_table("brands")
