"""add job observability fields

Revision ID: 20260702_009
Revises: 20260702_008
Create Date: 2026-07-02 20:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20260702_009'
down_revision: str | None = '20260702_008'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('last_stage', sa.String(length=255), nullable=True))
    op.add_column('jobs', sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'last_heartbeat_at')
    op.drop_column('jobs', 'last_stage')
