"""expand brand dna fields

Revision ID: 20260713_030
Revises: 20260707_029
Create Date: 2026-07-13 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = '20260713_030'
down_revision: str | None = '20260707_029'
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('brands', sa.Column('positioning', sa.Text(), nullable=True))
    op.add_column('brands', sa.Column('tone_of_voice', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('mission', sa.Text(), nullable=True))
    op.add_column('brands', sa.Column('values', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('forbidden_claims', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('allowed_claims', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('competitors', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('good_examples', sa.JSON(), nullable=True))
    op.add_column('brands', sa.Column('bad_examples', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('brands', 'bad_examples')
    op.drop_column('brands', 'good_examples')
    op.drop_column('brands', 'competitors')
    op.drop_column('brands', 'allowed_claims')
    op.drop_column('brands', 'forbidden_claims')
    op.drop_column('brands', 'values')
    op.drop_column('brands', 'mission')
    op.drop_column('brands', 'tone_of_voice')
    op.drop_column('brands', 'positioning')
