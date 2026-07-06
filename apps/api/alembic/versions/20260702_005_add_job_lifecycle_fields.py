"""add job lifecycle fields

Revision ID: 20260702_005
Revises: 20260702_004
Create Date: 2026-07-02 15:15:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260702_005"
down_revision: str | None = "20260702_004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "error_message")
    op.drop_column("jobs", "finished_at")
    op.drop_column("jobs", "started_at")
