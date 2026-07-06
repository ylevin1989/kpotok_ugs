"""create jobs table

Revision ID: 20260702_004
Revises: 20260702_003
Create Date: 2026-07-02 13:55:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260702_004"
down_revision: str | None = "20260702_003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("brief_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brief_id"], ["briefs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_organization_id", "jobs", ["organization_id"], unique=False)
    op.create_index("ix_jobs_brand_id", "jobs", ["brand_id"], unique=False)
    op.create_index("ix_jobs_brief_id", "jobs", ["brief_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_jobs_brief_id", table_name="jobs")
    op.drop_index("ix_jobs_brand_id", table_name="jobs")
    op.drop_index("ix_jobs_organization_id", table_name="jobs")
    op.drop_table("jobs")
