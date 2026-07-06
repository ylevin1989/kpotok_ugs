"""add job lease expiry

Revision ID: 20260702_007
Revises: 20260702_006
Create Date: 2026-07-02 19:05:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260702_007"
down_revision: str | None = "20260702_006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_jobs_lease_expires_at"), "jobs", ["lease_expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_lease_expires_at"), table_name="jobs")
    op.drop_column("jobs", "lease_expires_at")
