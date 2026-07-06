from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    organization_id: UUID = Field(description='Organization that owns the subscription.')
    plan_name: str = Field(default='free', description='Commercial plan name.')
    monthly_content_plan_limit: int = Field(default=25, ge=0, description='Monthly content-plan creation limit.')
    monthly_export_limit: int = Field(default=5, ge=0, description='Monthly export limit.')
    is_active: bool = Field(default=True, description='Whether the subscription is active.')
    current_period_start: date = Field(description='Current billing period start date.')
    current_period_end: date = Field(description='Current billing period end date.')


class SubscriptionRead(BaseModel):
    id: UUID
    organization_id: UUID
    plan_name: str
    monthly_content_plan_limit: int
    monthly_export_limit: int
    is_active: bool
    current_period_start: date
    current_period_end: date
    created_at: datetime
    updated_at: datetime


class SubscriptionListResponse(BaseModel):
    items: list[SubscriptionRead]


class UsageRecordRead(BaseModel):
    id: UUID
    organization_id: UUID
    subscription_id: UUID | None
    metric: str
    quantity: int
    window_start: datetime
    window_end: datetime
    metadata_json: str | None
    created_at: datetime


class UsageRecordListResponse(BaseModel):
    items: list[UsageRecordRead]
