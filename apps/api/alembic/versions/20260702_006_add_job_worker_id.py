"""add job worker ownership

Revision ID: 20260702_006
Revises: 20260702_005
Create Date: 2026-07-02 18:25:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260702_006"
down_revision: str | None = "20260702_005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("worker_id", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_jobs_worker_id"), "jobs", ["worker_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_worker_id"), table_name="jobs")
    op.drop_column("jobs", "worker_id")
