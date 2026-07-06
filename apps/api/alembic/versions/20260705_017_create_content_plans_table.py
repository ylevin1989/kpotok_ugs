"""create content plans table

Revision ID: 20260705_017
Revises: 20260704_016
Create Date: 2026-07-05 05:08:17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260705_017"
down_revision: str | None = "20260704_016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "content_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("audience_segment_id", sa.Uuid(), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default='brand'),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default='draft'),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["audience_segment_id"], ["audience_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("scope != 'product' OR product_id IS NOT NULL", name="ck_content_plans_product_scope_requires_product_id"),
    )
    op.create_index("ix_content_plans_organization_id", "content_plans", ["organization_id"], unique=False)
    op.create_index("ix_content_plans_brand_id", "content_plans", ["brand_id"], unique=False)
    op.create_index("ix_content_plans_product_id", "content_plans", ["product_id"], unique=False)
    op.create_index("ix_content_plans_audience_segment_id", "content_plans", ["audience_segment_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_content_plans_audience_segment_id", table_name="content_plans")
    op.drop_index("ix_content_plans_product_id", table_name="content_plans")
    op.drop_index("ix_content_plans_brand_id", table_name="content_plans")
    op.drop_index("ix_content_plans_organization_id", table_name="content_plans")
    op.drop_table("content_plans")
