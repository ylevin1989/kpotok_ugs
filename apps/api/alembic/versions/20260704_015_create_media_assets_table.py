"""create media assets table

Revision ID: 20260704_015
Revises: 20260704_014
Create Date: 2026-07-04 20:02:35
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260704_015"
down_revision: str | None = "20260704_014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default='brand'),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("asset_key", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "brand_id", "asset_key", name="uq_media_assets_org_brand_asset_key"),
        sa.CheckConstraint("scope != 'product' OR product_id IS NOT NULL", name="ck_media_assets_product_scope_requires_product_id"),
    )
    op.create_index("ix_media_assets_organization_id", "media_assets", ["organization_id"], unique=False)
    op.create_index("ix_media_assets_brand_id", "media_assets", ["brand_id"], unique=False)
    op.create_index("ix_media_assets_product_id", "media_assets", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_media_assets_product_id", table_name="media_assets")
    op.drop_index("ix_media_assets_brand_id", table_name="media_assets")
    op.drop_index("ix_media_assets_organization_id", table_name="media_assets")
    op.drop_table("media_assets")
