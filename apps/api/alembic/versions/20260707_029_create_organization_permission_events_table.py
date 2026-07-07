"""create organization permission events table

Revision ID: 20260707_029
Revises: 20260707_028
Create Date: 2026-07-07 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20260707_029'
down_revision: str | None = '20260707_028'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'organization_permission_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_membership_role', sa.String(length=32), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('target_type', sa.String(length=64), nullable=False),
        sa.Column('target_id', sa.String(length=64), nullable=False),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_organization_permission_events_organization_id'), 'organization_permission_events', ['organization_id'], unique=False)
    op.create_index(op.f('ix_organization_permission_events_actor_user_id'), 'organization_permission_events', ['actor_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_organization_permission_events_actor_user_id'), table_name='organization_permission_events')
    op.drop_index(op.f('ix_organization_permission_events_organization_id'), table_name='organization_permission_events')
    op.drop_table('organization_permission_events')
