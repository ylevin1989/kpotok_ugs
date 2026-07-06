"""add job execution trace json

Revision ID: 20260702_012
Revises: 20260702_011
Create Date: 2026-07-02 22:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260702_012'
down_revision = '20260702_011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('execution_trace_json', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'execution_trace_json')
