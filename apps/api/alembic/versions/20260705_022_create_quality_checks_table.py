"""create quality checks table

Revision ID: 20260705_022
Revises: 20260705_021
Create Date: 2026-07-05 11:18:17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260705_022'
down_revision: str | None = '20260705_021'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'quality_checks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('brand_id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('content_item_id', sa.UUID(), nullable=False),
        sa.Column('content_version_id', sa.UUID(), nullable=False),
        sa.Column('ticket_id', sa.UUID(), nullable=True),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('threshold', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('checks_json', sa.JSON(), nullable=False),
        sa.Column('issues_json', sa.JSON(), nullable=False),
        sa.Column('recommendations_json', sa.JSON(), nullable=False),
        sa.Column('generated_from_task_id', sa.UUID(), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['content_version_id'], ['content_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('score >= 0 AND score <= 100', name='ck_quality_checks_score_range'),
        sa.CheckConstraint('threshold >= 0 AND threshold <= 100', name='ck_quality_checks_threshold_range'),
    )
    op.create_index('ix_quality_checks_organization_id', 'quality_checks', ['organization_id'])
    op.create_index('ix_quality_checks_brand_id', 'quality_checks', ['brand_id'])
    op.create_index('ix_quality_checks_product_id', 'quality_checks', ['product_id'])
    op.create_index('ix_quality_checks_content_item_id', 'quality_checks', ['content_item_id'])
    op.create_index('ix_quality_checks_content_version_id', 'quality_checks', ['content_version_id'])
    op.create_index('ix_quality_checks_ticket_id', 'quality_checks', ['ticket_id'])
    op.create_index('ix_quality_checks_created_by_id', 'quality_checks', ['created_by_id'])
    op.create_index('ix_quality_checks_status', 'quality_checks', ['status'])


def downgrade() -> None:
    op.drop_index('ix_quality_checks_status', table_name='quality_checks')
    op.drop_index('ix_quality_checks_created_by_id', table_name='quality_checks')
    op.drop_index('ix_quality_checks_ticket_id', table_name='quality_checks')
    op.drop_index('ix_quality_checks_content_version_id', table_name='quality_checks')
    op.drop_index('ix_quality_checks_content_item_id', table_name='quality_checks')
    op.drop_index('ix_quality_checks_product_id', table_name='quality_checks')
    op.drop_index('ix_quality_checks_brand_id', table_name='quality_checks')
    op.drop_index('ix_quality_checks_organization_id', table_name='quality_checks')
    op.drop_table('quality_checks')
