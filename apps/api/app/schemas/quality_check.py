from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QualityCheckCreate(BaseModel):
    organization_id: UUID = Field(description='Owning organization.')
    content_version_id: UUID | None = Field(default=None, description='Content version to inspect; defaults to the current version on the item.')
    ticket_id: UUID | None = Field(default=None, description='Optional related review ticket.')
    threshold: int = Field(default=80, ge=0, le=100, description='Minimum acceptable quality threshold.')
    summary: str | None = Field(default=None, description='Optional human-readable note to attach to the computed result.')
    checks_json: dict = Field(default_factory=dict, description='Optional manual annotations to merge into the computed per-rule check results.')
    issues_json: list[str] = Field(default_factory=list, description='Optional manual issues to append to the computed result.')
    recommendations_json: list[str] = Field(default_factory=list, description='Optional manual recommendations to append to the computed result.')
    generated_from_task_id: UUID | None = Field(default=None, description='Optional Hermes task that produced the check.')
    checked_at: datetime | None = Field(default=None, description='Timestamp when the check was completed.')
    score: int | None = Field(default=None, ge=0, le=100, description='Deprecated manual override; computed automatically when omitted.')
    status: str | None = Field(default=None, description='Deprecated manual override; computed automatically.')


class QualityCheckRead(BaseModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    product_id: UUID | None
    content_item_id: UUID
    content_version_id: UUID
    ticket_id: UUID | None
    score: int
    threshold: int
    status: str
    summary: str | None
    checks_json: dict
    issues_json: list[str]
    recommendations_json: list[str]
    generated_from_task_id: UUID | None
    created_by_id: UUID | None
    checked_at: datetime
    created_at: datetime
    updated_at: datetime


class QualityCheckListResponse(BaseModel):
    items: list[QualityCheckRead]
