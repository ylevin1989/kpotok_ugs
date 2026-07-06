from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BrandCreate(BaseModel):
    organization_id: UUID
    name: str
    slug: str


class BrandUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None


class BrandRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    dna_json: dict | None = None
    created_at: datetime
    updated_at: datetime


class BrandListResponse(BaseModel):
    items: list[BrandRead]
