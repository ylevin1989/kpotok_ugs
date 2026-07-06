"""create briefs table

Revision ID: 20260702_003
Revises: 20260701_002
Create Date: 2026-07-02 12:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260702_003"
down_revision: str | None = "20260701_002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "briefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_briefs_organization_id", "briefs", ["organization_id"], unique=False)
    op.create_index("ix_briefs_brand_id", "briefs", ["brand_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_briefs_brand_id", table_name="briefs")
    op.drop_index("ix_briefs_organization_id", table_name="briefs")
    op.drop_table("briefs")
