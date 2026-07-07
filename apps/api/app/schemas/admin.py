from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models.organization import OrganizationStatus
from app.schemas.content_item import ContentItemRead


class AdminClientRead(BaseModel):
    id: UUID
    name: str
    slug: str
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime


class AdminClientListResponse(BaseModel):
    items: list[AdminClientRead]


class AdminContentReviewListResponse(BaseModel):
    items: list[ContentItemRead]
