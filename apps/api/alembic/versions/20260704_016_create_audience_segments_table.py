"""create audience segments table

Revision ID: 20260704_016
Revises: 20260704_015
Create Date: 2026-07-04 20:02:35
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260704_016"
down_revision: str | None = "20260704_015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audience_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default='brand'),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("pain_points", sa.JSON(), nullable=False),
        sa.Column("goals", sa.JSON(), nullable=False),
        sa.Column("objections", sa.JSON(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "brand_id", "name", name="uq_audience_segments_org_brand_name"),
        sa.CheckConstraint("scope != 'product' OR product_id IS NOT NULL", name="ck_audience_segments_product_scope_requires_product_id"),
    )
    op.create_index("ix_audience_segments_organization_id", "audience_segments", ["organization_id"], unique=False)
    op.create_index("ix_audience_segments_brand_id", "audience_segments", ["brand_id"], unique=False)
    op.create_index("ix_audience_segments_product_id", "audience_segments", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audience_segments_product_id", table_name="audience_segments")
    op.drop_index("ix_audience_segments_brand_id", table_name="audience_segments")
    op.drop_index("ix_audience_segments_organization_id", table_name="audience_segments")
    op.drop_table("audience_segments")
