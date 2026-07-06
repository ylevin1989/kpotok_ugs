"""add current_version_id to content_items

Revision ID: 20260705_020
Revises: 20260705_019
Create Date: 2026-07-05 07:07:46
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260705_020'
down_revision: str | Sequence[str] | None = '20260705_019'
branch_labels: Sequence[str] | str | None = None
depends_on: Sequence[str] | str | None = None


def upgrade() -> None:
    op.add_column('content_items', sa.Column('current_version_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_content_items_current_version_id'), 'content_items', ['current_version_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_content_items_current_version_id'), table_name='content_items')
    op.drop_column('content_items', 'current_version_id')
