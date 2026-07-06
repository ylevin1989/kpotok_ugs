"""create content items table

Revision ID: 20260705_018
Revises: 20260705_017
Create Date: 2026-07-05 07:07:46
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '20260705_018'
down_revision: str | None = '20260705_017'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'content_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('brand_id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=True),
        sa.Column('content_plan_id', sa.Uuid(), nullable=False),
        sa.Column('audience_segment_id', sa.Uuid(), nullable=True),
        sa.Column('scope', sa.String(length=32), nullable=False, server_default='brand'),
        sa.Column('platform', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=255), nullable=False),
        sa.Column('goal', sa.Text(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='draft'),
        sa.Column('quality_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['content_plan_id'], ['content_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['audience_segment_id'], ['audience_segments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("scope != 'product' OR product_id IS NOT NULL", name='ck_content_items_product_scope_requires_product_id'),
        sa.CheckConstraint('quality_score >= 0 AND quality_score <= 100', name='ck_content_items_quality_score_range'),
    )
    op.create_index('ix_content_items_organization_id', 'content_items', ['organization_id'], unique=False)
    op.create_index('ix_content_items_brand_id', 'content_items', ['brand_id'], unique=False)
    op.create_index('ix_content_items_product_id', 'content_items', ['product_id'], unique=False)
    op.create_index('ix_content_items_content_plan_id', 'content_items', ['content_plan_id'], unique=False)
    op.create_index('ix_content_items_audience_segment_id', 'content_items', ['audience_segment_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_content_items_audience_segment_id', table_name='content_items')
    op.drop_index('ix_content_items_content_plan_id', table_name='content_items')
    op.drop_index('ix_content_items_product_id', table_name='content_items')
    op.drop_index('ix_content_items_brand_id', table_name='content_items')
    op.drop_index('ix_content_items_organization_id', table_name='content_items')
    op.drop_table('content_items')
