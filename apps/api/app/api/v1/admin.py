from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_platform_admin
from app.db.models.audit_log import AuditLog
from app.db.models.content_item import ContentItem
from app.db.models.job import Job
from app.db.models.organization import Organization
from app.db.models.ticket import Ticket
from app.db.models.usage_record import UsageRecord
from app.db.models.user import User
from app.db.session import get_db
from app.domain.audit import record_audit
from app.schemas.admin import AdminClientListResponse, AdminClientRead, AdminContentReviewListResponse
from app.schemas.audit import AuditLogListResponse, AuditLogRead
from app.schemas.content_item import ContentItemRead
from app.schemas.job import JobListResponse, JobRead
from app.schemas.subscription import UsageRecordListResponse, UsageRecordRead
from app.schemas.ticket import TicketListResponse, TicketRead
from app.api.v1.jobs import _job_read

router = APIRouter(prefix='/admin', tags=['admin'])


def _request_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get('x-forwarded-for')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    if request.client is not None:
        return request.client.host
    return None


@router.get('/clients', response_model=AdminClientListResponse)
def list_clients(
    organization_id: UUID | None = Query(default=None),
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminClientListResponse:
    _ = admin_user
    query = select(Organization).order_by(Organization.created_at.desc(), Organization.id.desc())
    if organization_id is not None:
        query = query.where(Organization.id == organization_id)
    items = db.execute(query).scalars().all()
    return AdminClientListResponse(
        items=[
            AdminClientRead(
                id=item.id,
                name=item.name,
                slug=item.slug,
                status=item.status,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ]
    )


@router.get('/jobs', response_model=JobListResponse)
def list_admin_jobs(
    organization_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias='status'),
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> JobListResponse:
    _ = admin_user
    query = select(Job).order_by(Job.created_at.desc(), Job.id.desc())
    if organization_id is not None:
        query = query.where(Job.organization_id == organization_id)
    if status_filter is not None:
        query = query.where(Job.status == status_filter)
    jobs = db.execute(query).scalars().all()
    return JobListResponse(items=[_job_read(db, item) for item in jobs])


@router.post('/jobs/{job_id}/retry', response_model=JobRead)
def retry_job(
    job_id: UUID,
    request: Request,
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> JobRead:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Job not found')
    if job.status not in {'failed', 'cancelled'}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Only failed or cancelled jobs can be retried')
    old_status = job.status
    job.status = 'queued'
    job.worker_id = None
    job.lease_expires_at = None
    job.started_at = None
    job.finished_at = None
    job.error_message = None
    job.output_text = None
    job.output_artifact_key = None
    job.output_artifact_url = None
    job.output_artifact_content_type = None
    job.output_artifact_size_bytes = None
    job.output_artifact_etag = None
    job.last_stage = 'queued'
    record_audit(
        db,
        actor_user_id=admin_user.id,
        organization_id=job.organization_id,
        action='admin_job_retried',
        entity_type='job',
        entity_id=str(job.id),
        metadata={'from_status': old_status, 'to_status': 'queued'},
        ip=_request_ip(request),
    )
    db.commit()
    db.refresh(job)
    return _job_read(db, job)


@router.post('/jobs/{job_id}/cancel', response_model=JobRead)
def cancel_job(
    job_id: UUID,
    request: Request,
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> JobRead:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Job not found')
    if job.status not in {'queued', 'running'}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Only queued or running jobs can be cancelled')
    old_status = job.status
    job.status = 'cancelled'
    job.worker_id = None
    job.lease_expires_at = None
    job.finished_at = datetime.now(timezone.utc)
    job.error_message = 'Cancelled by platform admin'
    job.last_stage = 'cancelled'
    record_audit(
        db,
        actor_user_id=admin_user.id,
        organization_id=job.organization_id,
        action='admin_job_cancelled',
        entity_type='job',
        entity_id=str(job.id),
        metadata={'from_status': old_status, 'to_status': 'cancelled'},
        ip=_request_ip(request),
    )
    db.commit()
    db.refresh(job)
    return _job_read(db, job)


@router.get('/tickets', response_model=TicketListResponse)
def list_admin_tickets(
    organization_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias='status'),
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> TicketListResponse:
    _ = admin_user
    query = select(Ticket).order_by(Ticket.created_at.desc(), Ticket.id.desc())
    if organization_id is not None:
        query = query.where(Ticket.organization_id == organization_id)
    if status_filter is not None:
        query = query.where(Ticket.status == status_filter)
    tickets = db.execute(query).scalars().all()
    return TicketListResponse(items=[TicketRead.model_validate(item, from_attributes=True) for item in tickets])


@router.get('/content-review', response_model=AdminContentReviewListResponse)
def list_content_review(
    organization_id: UUID | None = Query(default=None),
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminContentReviewListResponse:
    _ = admin_user
    query = select(ContentItem).where(ContentItem.status == 'internal_review').order_by(ContentItem.created_at.desc(), ContentItem.id.desc())
    if organization_id is not None:
        query = query.where(ContentItem.organization_id == organization_id)
    items = db.execute(query).scalars().all()
    return AdminContentReviewListResponse(items=[ContentItemRead.model_validate(item, from_attributes=True) for item in items])


@router.get('/usage', response_model=UsageRecordListResponse)
def list_admin_usage(
    organization_id: UUID | None = Query(default=None),
    metric: str | None = Query(default=None),
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> UsageRecordListResponse:
    _ = admin_user
    query = select(UsageRecord).order_by(UsageRecord.created_at.desc(), UsageRecord.id.desc())
    if organization_id is not None:
        query = query.where(UsageRecord.organization_id == organization_id)
    if metric is not None:
        query = query.where(UsageRecord.metric == metric)
    records = db.execute(query).scalars().all()
    return UsageRecordListResponse(items=[UsageRecordRead.model_validate(item, from_attributes=True) for item in records])


@router.get('/audit-logs', response_model=AuditLogListResponse)
def list_audit_logs(
    organization_id: UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    admin_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    _ = admin_user
    query = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    if organization_id is not None:
        query = query.where(AuditLog.organization_id == organization_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    if entity_type is not None:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(AuditLog.entity_id == entity_id)
    items = db.execute(query).scalars().all()
    return AuditLogListResponse(items=[AuditLogRead.model_validate(item, from_attributes=True) for item in items])
