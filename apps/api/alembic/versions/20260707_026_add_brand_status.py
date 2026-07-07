"""add brand status

Revision ID: 20260707_026
Revises: 20260706_025
Create Date: 2026-07-07 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = '20260707_026'
down_revision: str | None = '20260706_025'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    brand_status = sa.Enum('active', 'paused', 'archived', name='brand_status')
    brand_status.create(op.get_bind(), checkfirst=True)
    op.add_column('brands', sa.Column('status', brand_status, nullable=False, server_default='active'))
    op.alter_column('brands', 'status', server_default=None)


def downgrade() -> None:
    op.drop_column('brands', 'status')
    sa.Enum(name='brand_status').drop(op.get_bind(), checkfirst=True)
