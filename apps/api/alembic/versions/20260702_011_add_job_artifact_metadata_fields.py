"""add job artifact metadata fields

Revision ID: 20260702_011
Revises: 20260702_010
Create Date: 2026-07-02 21:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20260702_011'
down_revision: str | None = '20260702_010'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('output_artifact_size_bytes', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('output_artifact_etag', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'output_artifact_etag')
    op.drop_column('jobs', 'output_artifact_size_bytes')
