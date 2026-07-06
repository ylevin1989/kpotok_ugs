from __future__ import annotations

from datetime import datetime, timezone
import json
from calendar import monthrange
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.subscription import Subscription
from app.db.models.usage_record import UsageRecord

DEFAULT_PLAN_NAME = 'free'
DEFAULT_CONTENT_PLAN_LIMIT = 25
DEFAULT_EXPORT_LIMIT = 5

CONTENT_PLAN_GENERATION_METRIC = 'content_plan_generation'
CONTENT_PLAN_EXPORT_METRIC = 'content_plan_export'


def month_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    current = now or datetime.now(timezone.utc)
    start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_day = monthrange(current.year, current.month)[1]
    end = current.replace(day=end_day, hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def _usage_sum(db: Session, organization_id: UUID, metric: str, window_start: datetime, window_end: datetime) -> int:
    total = db.execute(
        select(func.coalesce(func.sum(UsageRecord.quantity), 0)).where(
            UsageRecord.organization_id == organization_id,
            UsageRecord.metric == metric,
            UsageRecord.window_start >= window_start,
            UsageRecord.window_end <= window_end,
        )
    ).scalar_one()
    return int(total or 0)


def get_or_create_subscription(db: Session, organization_id: UUID) -> Subscription:
    subscription = db.execute(
        select(Subscription).where(Subscription.organization_id == organization_id).order_by(Subscription.created_at.desc())
    ).scalars().first()
    if subscription is not None:
        return subscription

    now = datetime.now(timezone.utc)
    subscription = Subscription(
        organization_id=organization_id,
        plan_name=DEFAULT_PLAN_NAME,
        monthly_content_plan_limit=DEFAULT_CONTENT_PLAN_LIMIT,
        monthly_export_limit=DEFAULT_EXPORT_LIMIT,
        is_active=True,
        current_period_start=now.date().replace(day=1),
        current_period_end=month_window(now)[1].date(),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def record_usage(db: Session, *, organization_id: UUID, subscription: Subscription | None, metric: str, quantity: int, metadata: dict[str, Any] | None = None) -> UsageRecord:
    window_start, window_end = month_window()
    usage = UsageRecord(
        organization_id=organization_id,
        subscription_id=subscription.id if subscription is not None else None,
        metric=metric,
        quantity=quantity,
        window_start=window_start,
        window_end=window_end,
        metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata is not None else None,
    )
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage


def enforce_usage_limit(db: Session, *, organization_id: UUID, metric: str, quantity: int, limit: int, error_detail: str) -> None:
    if limit <= 0:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_detail)
    window_start, window_end = month_window()
    current_usage = _usage_sum(db, organization_id, metric, window_start, window_end)
    if current_usage + quantity > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_detail)


def current_usage_summary(db: Session, organization_id: UUID) -> dict[str, int]:
    window_start, window_end = month_window()
    return {
        CONTENT_PLAN_GENERATION_METRIC: _usage_sum(db, organization_id, CONTENT_PLAN_GENERATION_METRIC, window_start, window_end),
        CONTENT_PLAN_EXPORT_METRIC: _usage_sum(db, organization_id, CONTENT_PLAN_EXPORT_METRIC, window_start, window_end),
    }
