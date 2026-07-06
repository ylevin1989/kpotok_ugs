from datetime import date as DateType, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.content_scope import ContentScope, requires_product_id


class ContentPlanCreate(BaseModel):
    organization_id: UUID = Field(description='Organization that owns the content plan.')
    brand_id: UUID = Field(description='Brand scope for the content plan.')
    product_id: UUID | None = Field(default=None, description='Required when scope is product.')
    audience_segment_id: UUID | None = Field(default=None, description='Optional audience segment linked to the plan.')
    scope: ContentScope = Field(default=ContentScope.BRAND, description='Content plan scope.')
    date: DateType = Field(description='Publishing date for the plan.')
    title: str = Field(description='Human-readable content plan title.')
    platform: str = Field(description='Publishing platform or channel.')
    content_type: str = Field(description='Planned content type.')
    goal: str = Field(description='Planning goal or campaign objective.')
    status: str = Field(default='draft', description='Content plan lifecycle status.')

    @model_validator(mode='after')
    def validate_scope_requirements(self) -> 'ContentPlanCreate':
        if requires_product_id(self.scope) and self.product_id is None:
            raise ValueError('product_id is required when scope is product')
        return self


class ContentPlanRead(BaseModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    product_id: UUID | None
    audience_segment_id: UUID | None
    scope: ContentScope
    date: DateType
    title: str
    platform: str
    content_type: str
    goal: str
    status: str
    created_at: datetime
    updated_at: datetime


class ContentPlanListResponse(BaseModel):
    items: list[ContentPlanRead]
