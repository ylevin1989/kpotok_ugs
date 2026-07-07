"""create exports table

Revision ID: 20260707_027
Revises: 20260707_026
Create Date: 2026-07-07 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20260707_027'
down_revision: str | None = '20260707_026'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    export_format = sa.Enum('markdown', 'csv', 'zip', name='export_format')
    export_status = sa.Enum('pending', 'ready', 'failed', name='export_status')
    export_format.create(op.get_bind(), checkfirst=True)
    export_status.create(op.get_bind(), checkfirst=True)
    export_format_column = postgresql.ENUM('markdown', 'csv', 'zip', name='export_format', create_type=False)
    export_status_column = postgresql.ENUM('pending', 'ready', 'failed', name='export_status', create_type=False)

    op.create_table(
        'exports',
        sa.Column('brand_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brands.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('content_plans.id', ondelete='SET NULL'), nullable=True),
        sa.Column('format', export_format_column, nullable=False),
        sa.Column('status', export_status_column, nullable=False, server_default='pending'),
        sa.Column('filter_json', sa.JSON(), nullable=True),
        sa.Column('file_key', sa.String(length=1024), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('content_type', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_exports_brand_id'), 'exports', ['brand_id'], unique=False)
    op.create_index(op.f('ix_exports_content_plan_id'), 'exports', ['content_plan_id'], unique=False)
    op.create_index(op.f('ix_exports_organization_id'), 'exports', ['organization_id'], unique=False)
    op.create_index(op.f('ix_exports_status'), 'exports', ['status'], unique=False)
    op.alter_column('exports', 'status', server_default=None)


def downgrade() -> None:
    op.drop_index(op.f('ix_exports_status'), table_name='exports')
    op.drop_index(op.f('ix_exports_organization_id'), table_name='exports')
    op.drop_index(op.f('ix_exports_content_plan_id'), table_name='exports')
    op.drop_index(op.f('ix_exports_brand_id'), table_name='exports')
    op.drop_table('exports')
    sa.Enum(name='export_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='export_format').drop(op.get_bind(), checkfirst=True)
