"""create products table

Revision ID: 20260704_014
Revises: 20260704_013
Create Date: 2026-07-04 20:02:35
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260704_014"
down_revision: str | None = "20260704_013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("benefits", sa.JSON(), nullable=False),
        sa.Column("proofs", sa.JSON(), nullable=False),
        sa.Column("objections", sa.JSON(), nullable=False),
        sa.Column("restrictions", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("readiness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "brand_id", "sku", name="uq_products_org_brand_sku"),
        sa.CheckConstraint("readiness_score >= 0 AND readiness_score <= 100", name="ck_products_readiness_score_range"),
    )
    op.create_index("ix_products_organization_id", "products", ["organization_id"], unique=False)
    op.create_index("ix_products_brand_id", "products", ["brand_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_products_brand_id", table_name="products")
    op.drop_index("ix_products_organization_id", table_name="products")
    op.drop_table("products")
