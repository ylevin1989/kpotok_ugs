"""add internal execution role plan fields to jobs

Revision ID: 20260704_013
Revises: 20260702_012
Create Date: 2026-07-04 06:50:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260704_013'
down_revision: Union[str, Sequence[str], None] = '20260702_012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('execution_profile', sa.String(length=64), nullable=False, server_default='general_content'))
    op.add_column('jobs', sa.Column('internal_role_plan_json', sa.Text(), nullable=True))
    op.alter_column('jobs', 'execution_profile', server_default=None)


def downgrade() -> None:
    op.drop_column('jobs', 'internal_role_plan_json')
    op.drop_column('jobs', 'execution_profile')
