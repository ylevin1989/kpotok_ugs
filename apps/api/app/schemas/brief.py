from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BriefCreate(BaseModel):
    organization_id: UUID
    brand_id: UUID
    title: str
    content: str


class BriefRead(BaseModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class BriefListResponse(BaseModel):
    items: list[BriefRead]
