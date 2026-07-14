from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models.brand import BrandStatus


class BrandCreate(BaseModel):
    organization_id: UUID
    name: str
    slug: str
    status: BrandStatus | None = None
    positioning: str | None = None
    tone_of_voice: list | None = None
    mission: str | None = None
    values: list | None = None
    forbidden_claims: list | None = None
    allowed_claims: list | None = None
    competitors: list | None = None
    good_examples: list | None = None
    bad_examples: list | None = None


class BrandUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    status: BrandStatus | None = None
    positioning: str | None = None
    tone_of_voice: list | None = None
    mission: str | None = None
    values: list | None = None
    forbidden_claims: list | None = None
    allowed_claims: list | None = None
    competitors: list | None = None
    good_examples: list | None = None
    bad_examples: list | None = None


class BrandRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    status: BrandStatus
    dna_json: dict | None = None
    positioning: str | None = None
    tone_of_voice: list | None = None
    mission: str | None = None
    values: list | None = None
    forbidden_claims: list | None = None
    allowed_claims: list | None = None
    competitors: list | None = None
    good_examples: list | None = None
    bad_examples: list | None = None
    created_at: datetime
    updated_at: datetime


class BrandListResponse(BaseModel):
    items: list[BrandRead]
