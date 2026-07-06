"""create auth and organization tables

Revision ID: 20260701_001
Revises: 
Create Date: 2026-07-01 12:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260701_001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


platform_role = postgresql.ENUM("super_admin", "platform_admin", name="platform_role", create_type=False)
organization_status = postgresql.ENUM("active", "paused", "archived", name="organization_status", create_type=False)
membership_role = postgresql.ENUM("client_owner", "client_manager", "client_reviewer", name="membership_role", create_type=False)


def upgrade() -> None:
    op.execute("""
    DO $$
    BEGIN
        CREATE TYPE platform_role AS ENUM ('super_admin', 'platform_admin');
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END $$;
    """)
    op.execute("""
    DO $$
    BEGIN
        CREATE TYPE organization_status AS ENUM ('active', 'paused', 'archived');
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END $$;
    """)
    op.execute("""
    DO $$
    BEGIN
        CREATE TYPE membership_role AS ENUM ('client_owner', 'client_manager', 'client_reviewer');
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END $$;
    """)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("platform_role", platform_role, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("status", organization_status, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", membership_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_membership_org_user"),
    )
    op.create_index("ix_organization_memberships_organization_id", "organization_memberships", ["organization_id"], unique=False)
    op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_organization_memberships_user_id", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_organization_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    membership_role.drop(bind, checkfirst=True)
    organization_status.drop(bind, checkfirst=True)
    platform_role.drop(bind, checkfirst=True)
