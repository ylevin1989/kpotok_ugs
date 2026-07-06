"""add dna json to brands and products

Revision ID: 20260706_023
Revises: 20260705_022
Create Date: 2026-07-06 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260706_023'
down_revision: str | None = '20260705_022'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('brands', sa.Column('dna_json', sa.JSON(), nullable=True))
    op.add_column('products', sa.Column('dna_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'dna_json')
    op.drop_column('brands', 'dna_json')
