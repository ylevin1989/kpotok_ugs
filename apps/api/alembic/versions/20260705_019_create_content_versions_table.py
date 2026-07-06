"""create content versions table

Revision ID: 20260705_019
Revises: 20260705_018
Create Date: 2026-07-05 07:07:46
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '20260705_019'
down_revision: str | None = '20260705_018'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'content_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('content_item_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('body_markdown', sa.Text(), nullable=True),
        sa.Column('structured_json', sa.JSON(), nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('generation_type', sa.String(length=32), nullable=False),
        sa.Column('generated_from_task_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_item_id', 'version_number', name='uq_content_versions_item_version'),
        sa.CheckConstraint('version_number > 0', name='ck_content_versions_version_number_positive'),
    )
    op.create_index(op.f('ix_content_versions_content_item_id'), 'content_versions', ['content_item_id'], unique=False)
    op.create_index(op.f('ix_content_versions_organization_id'), 'content_versions', ['organization_id'], unique=False)
    op.create_index(op.f('ix_content_versions_is_current'), 'content_versions', ['is_current'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_content_versions_is_current'), table_name='content_versions')
    op.drop_index(op.f('ix_content_versions_organization_id'), table_name='content_versions')
    op.drop_index(op.f('ix_content_versions_content_item_id'), table_name='content_versions')
    op.drop_table('content_versions')
