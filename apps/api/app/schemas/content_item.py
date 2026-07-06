from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.content_scope import ContentScope, requires_product_id


class ContentItemCreate(BaseModel):
    organization_id: UUID = Field(description='Organization that owns the content item.')
    brand_id: UUID = Field(description='Brand scope for the content item.')
    product_id: UUID | None = Field(default=None, description='Required when scope is product.')
    content_plan_id: UUID = Field(description='Parent content plan.')
    audience_segment_id: UUID | None = Field(default=None, description='Optional audience segment linked to the item.')
    scope: ContentScope = Field(default=ContentScope.BRAND, description='Content item scope.')
    platform: str = Field(description='Publishing platform or channel.')
    content_type: str = Field(description='Content format or type.')
    goal: str = Field(description='Goal or objective for the content item.')
    title: str = Field(description='Human-readable content item title.')
    status: str = Field(default='draft', description='Content item lifecycle status.')
    quality_score: int = Field(default=0, ge=0, le=100, description='Quality score on a 0-100 scale.')

    @model_validator(mode='after')
    def validate_scope_requirements(self) -> 'ContentItemCreate':
        if requires_product_id(self.scope) and self.product_id is None:
            raise ValueError('product_id is required when scope is product')
        return self


class ContentItemRead(BaseModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    product_id: UUID | None
    content_plan_id: UUID
    audience_segment_id: UUID | None
    current_version_id: UUID | None
    scope: ContentScope
    platform: str
    content_type: str
    goal: str
    title: str
    status: str
    quality_score: int
    created_at: datetime
    updated_at: datetime


class ContentItemListResponse(BaseModel):
    items: list[ContentItemRead]
