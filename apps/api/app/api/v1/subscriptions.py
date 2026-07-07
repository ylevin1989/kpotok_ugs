from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_current_user, get_organization_membership, require_organization_manager
from app.api.v1.organizations import ensure_content_organization_writable
from app.db.models.organization import Organization, OrganizationMembership
from app.db.models.subscription import Subscription
from app.db.models.usage_record import UsageRecord
from app.db.models.user import User
from app.db.session import get_db
from app.domain.audit import record_audit
from app.domain.billing import get_or_create_subscription, current_usage_summary
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionListResponse,
    SubscriptionRead,
    UsageRecordListResponse,
    UsageRecordRead,
)

router = APIRouter(prefix='/subscriptions', tags=['subscriptions'])


def _request_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get('x-forwarded-for')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    if request.client is not None:
        return request.client.host
    return None


@router.get('', response_model=SubscriptionListResponse)
def list_subscriptions(
    organization_id: UUID = Query(...),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> SubscriptionListResponse:
    get_organization_membership(organization_id, memberships)
    subscription = get_or_create_subscription(db, organization_id)
    return SubscriptionListResponse(items=[SubscriptionRead.model_validate(subscription, from_attributes=True)])


@router.post('', response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def upsert_subscription(
    payload: SubscriptionCreate,
    request: Request,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found')
    ensure_content_organization_writable(organization)
    subscription = db.execute(
        select(Subscription).where(Subscription.organization_id == payload.organization_id)
    ).scalars().first()
    if subscription is None:
        subscription = Subscription(
            organization_id=payload.organization_id,
            plan_name=payload.plan_name,
            monthly_content_plan_limit=payload.monthly_content_plan_limit,
            monthly_export_limit=payload.monthly_export_limit,
            is_active=payload.is_active,
            current_period_start=payload.current_period_start,
            current_period_end=payload.current_period_end,
        )
        db.add(subscription)
        action = 'subscription_upserted'
    else:
        subscription.plan_name = payload.plan_name
        subscription.monthly_content_plan_limit = payload.monthly_content_plan_limit
        subscription.monthly_export_limit = payload.monthly_export_limit
        subscription.is_active = payload.is_active
        subscription.current_period_start = payload.current_period_start
        subscription.current_period_end = payload.current_period_end
        action = 'subscription_upserted'
    db.flush()
    record_audit(
        db,
        actor_user_id=current_user.id,
        organization_id=payload.organization_id,
        action=action,
        entity_type='subscription',
        entity_id=str(subscription.id),
        metadata={
            'plan_name': payload.plan_name,
            'monthly_content_plan_limit': payload.monthly_content_plan_limit,
            'monthly_export_limit': payload.monthly_export_limit,
            'is_active': payload.is_active,
            'current_period_start': payload.current_period_start.isoformat(),
            'current_period_end': payload.current_period_end.isoformat(),
        },
        ip=_request_ip(request),
    )
    db.commit()
    db.refresh(subscription)
    return SubscriptionRead.model_validate(subscription, from_attributes=True)


@router.get('/usage', response_model=UsageRecordListResponse)
def list_usage_records(
    organization_id: UUID = Query(...),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> UsageRecordListResponse:
    get_organization_membership(organization_id, memberships)
    subscription = get_or_create_subscription(db, organization_id)
    records = db.execute(
        select(UsageRecord)
        .where(UsageRecord.organization_id == organization_id, UsageRecord.subscription_id == subscription.id)
        .order_by(UsageRecord.created_at.desc())
    ).scalars().all()
    return UsageRecordListResponse(items=[UsageRecordRead.model_validate(item, from_attributes=True) for item in records])
