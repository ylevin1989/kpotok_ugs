"""add explicit job kind and typed target references

Revision ID: 20260706_025
Revises: 20260706_024
Create Date: 2026-07-06 00:00:00
"""

from collections.abc import Sequence
import json

from alembic import op
import sqlalchemy as sa


revision: str = '20260706_025'
down_revision: str | None = '20260706_024'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _infer_job_kind_and_targets(brief_content: str | None) -> tuple[str, dict[str, str | None]]:
    defaults = {
        'target_brand_id': None,
        'target_product_id': None,
        'target_content_item_id': None,
        'target_ticket_id': None,
    }
    if not brief_content:
        return 'manual', defaults
    try:
        payload = json.loads(brief_content)
    except json.JSONDecodeError:
        return 'manual', defaults
    if not isinstance(payload, dict):
        return 'manual', defaults

    kind = payload.get('kind')
    if kind == 'content_item_generation':
        return 'content_generation', {
            'target_brand_id': payload.get('brand_id'),
            'target_product_id': payload.get('product_id'),
            'target_content_item_id': payload.get('content_item_id'),
            'target_ticket_id': None,
        }
    if kind == 'brand_dna_generation':
        return 'dna_generation', {
            'target_brand_id': payload.get('brand_id'),
            'target_product_id': None,
            'target_content_item_id': None,
            'target_ticket_id': None,
        }
    if kind == 'product_dna_generation':
        return 'dna_generation', {
            'target_brand_id': payload.get('brand_id'),
            'target_product_id': payload.get('product_id'),
            'target_content_item_id': None,
            'target_ticket_id': None,
        }
    if kind == 'content_item_ticket_revision':
        return 'ticket_processing', {
            'target_brand_id': payload.get('brand_id'),
            'target_product_id': payload.get('product_id'),
            'target_content_item_id': payload.get('content_item_id'),
            'target_ticket_id': payload.get('ticket_id'),
        }
    return 'manual', defaults


def upgrade() -> None:
    op.add_column('jobs', sa.Column('kind', sa.String(length=64), nullable=True, server_default='manual'))
    op.add_column('jobs', sa.Column('target_brand_id', sa.Uuid(), nullable=True))
    op.add_column('jobs', sa.Column('target_product_id', sa.Uuid(), nullable=True))
    op.add_column('jobs', sa.Column('target_content_item_id', sa.Uuid(), nullable=True))
    op.add_column('jobs', sa.Column('target_ticket_id', sa.Uuid(), nullable=True))
    op.create_index('ix_jobs_kind', 'jobs', ['kind'], unique=False)
    op.create_index('ix_jobs_target_brand_id', 'jobs', ['target_brand_id'], unique=False)
    op.create_index('ix_jobs_target_product_id', 'jobs', ['target_product_id'], unique=False)
    op.create_index('ix_jobs_target_content_item_id', 'jobs', ['target_content_item_id'], unique=False)
    op.create_index('ix_jobs_target_ticket_id', 'jobs', ['target_ticket_id'], unique=False)

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            'SELECT jobs.id AS job_id, briefs.content AS brief_content '\
            'FROM jobs JOIN briefs ON briefs.id = jobs.brief_id'
        )
    ).mappings().all()
    for row in rows:
        kind, targets = _infer_job_kind_and_targets(row['brief_content'])
        bind.execute(
            sa.text(
                'UPDATE jobs SET kind = :kind, target_brand_id = :target_brand_id, '\
                'target_product_id = :target_product_id, target_content_item_id = :target_content_item_id, '\
                'target_ticket_id = :target_ticket_id WHERE id = :job_id'
            ),
            {
                'job_id': row['job_id'],
                'kind': kind,
                **targets,
            },
        )

    op.alter_column('jobs', 'kind', existing_type=sa.String(length=64), nullable=False, server_default='manual')


def downgrade() -> None:
    op.alter_column('jobs', 'kind', existing_type=sa.String(length=64), nullable=True, server_default=None)
    op.drop_index('ix_jobs_target_ticket_id', table_name='jobs')
    op.drop_index('ix_jobs_target_content_item_id', table_name='jobs')
    op.drop_index('ix_jobs_target_product_id', table_name='jobs')
    op.drop_index('ix_jobs_target_brand_id', table_name='jobs')
    op.drop_index('ix_jobs_kind', table_name='jobs')
    op.drop_column('jobs', 'target_ticket_id')
    op.drop_column('jobs', 'target_content_item_id')
    op.drop_column('jobs', 'target_product_id')
    op.drop_column('jobs', 'target_brand_id')
    op.drop_column('jobs', 'kind')
