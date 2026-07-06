"""create tickets table

Revision ID: 20260705_021
Revises: 20260705_020
Create Date: 2026-07-05 08:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260705_021'
down_revision: str | Sequence[str] | None = '20260705_020'
branch_labels: Sequence[str] | str | None = None
depends_on: Sequence[str] | str | None = None


def upgrade() -> None:
    op.create_table(
        'tickets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('brand_id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('content_item_id', sa.UUID(), nullable=False),
        sa.Column('content_version_id', sa.UUID(), nullable=True),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('reason_codes', sa.JSON(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('priority', sa.String(length=32), nullable=False),
        sa.Column('assigned_agent_role', sa.String(length=64), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['content_version_id'], ['content_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tickets_assigned_agent_role'), 'tickets', ['assigned_agent_role'], unique=False)
    op.create_index(op.f('ix_tickets_brand_id'), 'tickets', ['brand_id'], unique=False)
    op.create_index(op.f('ix_tickets_content_item_id'), 'tickets', ['content_item_id'], unique=False)
    op.create_index(op.f('ix_tickets_content_version_id'), 'tickets', ['content_version_id'], unique=False)
    op.create_index(op.f('ix_tickets_created_by_id'), 'tickets', ['created_by_id'], unique=False)
    op.create_index(op.f('ix_tickets_organization_id'), 'tickets', ['organization_id'], unique=False)
    op.create_index(op.f('ix_tickets_priority'), 'tickets', ['priority'], unique=False)
    op.create_index(op.f('ix_tickets_product_id'), 'tickets', ['product_id'], unique=False)
    op.create_index(op.f('ix_tickets_status'), 'tickets', ['status'], unique=False)
    op.create_index(op.f('ix_tickets_type'), 'tickets', ['type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tickets_type'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_status'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_product_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_priority'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_organization_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_created_by_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_content_version_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_content_item_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_brand_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_assigned_agent_role'), table_name='tickets')
    op.drop_table('tickets')
