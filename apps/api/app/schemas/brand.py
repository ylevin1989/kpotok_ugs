from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models.brand import BrandStatus


class BrandCreate(BaseModel):
    organization_id: UUID
    name: str
    slug: str
    status: BrandStatus | None = None


class BrandUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    status: BrandStatus | None = None


class BrandRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    status: BrandStatus
    dna_json: dict | None = None
    created_at: datetime
    updated_at: datetime


class BrandListResponse(BaseModel):
    items: list[BrandRead]
