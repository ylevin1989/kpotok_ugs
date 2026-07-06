"""add job attempt count and output text

Revision ID: 20260702_008
Revises: 20260702_007
Create Date: 2026-07-02 20:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20260702_008'
down_revision: str | None = '20260702_007'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('jobs', sa.Column('output_text', sa.Text(), nullable=True))
    op.alter_column('jobs', 'attempt_count', server_default=None)


def downgrade() -> None:
    op.drop_column('jobs', 'output_text')
    op.drop_column('jobs', 'attempt_count')
