"""create subscriptions and usage records tables

Revision ID: 20260706_024
Revises: 20260706_023
Create Date: 2026-07-06 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = '20260706_024'
down_revision: str | None = '20260706_023'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('plan_name', sa.String(length=64), nullable=False, server_default='free'),
        sa.Column('monthly_content_plan_limit', sa.Integer(), nullable=False, server_default='25'),
        sa.Column('monthly_export_limit', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('current_period_start', sa.Date(), nullable=False),
        sa.Column('current_period_end', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', name='uq_subscriptions_organization_id'),
    )
    op.create_index('ix_subscriptions_organization_id', 'subscriptions', ['organization_id'], unique=False)

    op.create_table(
        'usage_records',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('subscription_id', sa.Uuid(), nullable=True),
        sa.Column('metric', sa.String(length=64), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_usage_records_organization_id', 'usage_records', ['organization_id'], unique=False)
    op.create_index('ix_usage_records_subscription_id', 'usage_records', ['subscription_id'], unique=False)
    op.create_index('ix_usage_records_metric', 'usage_records', ['metric'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_usage_records_metric', table_name='usage_records')
    op.drop_index('ix_usage_records_subscription_id', table_name='usage_records')
    op.drop_index('ix_usage_records_organization_id', table_name='usage_records')
    op.drop_table('usage_records')
    op.drop_index('ix_subscriptions_organization_id', table_name='subscriptions')
    op.drop_table('subscriptions')
