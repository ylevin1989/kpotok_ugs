from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    organization_id: UUID = Field(description='Organization that owns the product.')
    brand_id: UUID = Field(description='Brand scope for the product.')
    sku: str = Field(description='Stable product SKU within the organization/brand scope.')
    name: str = Field(description='Human-readable product name.')
    category: str = Field(description='Product category.')
    description: str = Field(description='Canonical product description.')
    features: list[str] = Field(default_factory=list, description='Key product features.')
    benefits: list[str] = Field(default_factory=list, description='Customer-facing benefits.')
    proofs: list[str] = Field(default_factory=list, description='Proof points, evidence, or credibility signals.')
    objections: list[str] = Field(default_factory=list, description='Expected objections or friction points.')
    restrictions: list[str] = Field(default_factory=list, description='Product or compliance restrictions.')
    status: str = Field(default='draft', description='Product lifecycle status.')
    readiness_score: int = Field(default=0, description='Readiness score on a 0-100 scale.')


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, description='Stable product SKU within the organization/brand scope.')
    name: str | None = Field(default=None, description='Human-readable product name.')
    category: str | None = Field(default=None, description='Product category.')
    description: str | None = Field(default=None, description='Canonical product description.')
    features: list[str] | None = Field(default=None, description='Key product features.')
    benefits: list[str] | None = Field(default=None, description='Customer-facing benefits.')
    proofs: list[str] | None = Field(default=None, description='Proof points, evidence, or credibility signals.')
    objections: list[str] | None = Field(default=None, description='Expected objections or friction points.')
    restrictions: list[str] | None = Field(default=None, description='Product or compliance restrictions.')
    status: str | None = Field(default=None, description='Product lifecycle status.')
    readiness_score: int | None = Field(default=None, description='Readiness score on a 0-100 scale.')


class ProductRead(BaseModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    sku: str
    name: str
    category: str
    description: str
    features: list[str]
    benefits: list[str]
    proofs: list[str]
    objections: list[str]
    restrictions: list[str]
    dna_json: dict | None = None
    status: str
    readiness_score: int
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductRead]
