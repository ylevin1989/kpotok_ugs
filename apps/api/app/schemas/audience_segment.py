from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.content_scope import ContentScope, requires_product_id


class AudienceSegmentCreate(BaseModel):
    organization_id: UUID = Field(description='Organization that owns the audience segment.')
    brand_id: UUID = Field(description='Brand scope for the audience segment.')
    product_id: UUID | None = Field(default=None, description='Required when scope is product.')
    scope: ContentScope = Field(default=ContentScope.BRAND, description='Audience segment scope.')
    name: str = Field(description='Human-readable audience segment name.')
    description: str = Field(description='Canonical segment description.')
    pain_points: list[str] = Field(default_factory=list, description='Observed pain points for this segment.')
    goals: list[str] = Field(default_factory=list, description='Primary goals or desired outcomes.')
    objections: list[str] = Field(default_factory=list, description='Likely objections or barriers.')
    keywords: list[str] = Field(default_factory=list, description='Useful search or topic keywords.')

    @model_validator(mode='after')
    def validate_scope_requirements(self) -> 'AudienceSegmentCreate':
        if requires_product_id(self.scope) and self.product_id is None:
            raise ValueError('product_id is required when scope is product')
        return self


class AudienceSegmentRead(BaseModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    product_id: UUID | None
    scope: ContentScope
    name: str
    description: str
    pain_points: list[str]
    goals: list[str]
    objections: list[str]
    keywords: list[str]
    created_at: datetime
    updated_at: datetime


class AudienceSegmentListResponse(BaseModel):
    items: list[AudienceSegmentRead]
