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


class ContentPlanGenerate(BaseModel):
    organization_id: UUID = Field(description='Organization that owns the generated content plans.')
    brand_id: UUID = Field(description='Brand scope for the generated content plans.')
    product_id: UUID | None = Field(default=None, description='Required when scope is product.')
    audience_segment_id: UUID | None = Field(default=None, description='Optional audience segment linked to the generated plans.')
    scope: ContentScope = Field(default=ContentScope.BRAND, description='Generation scope.')
    start_date: DateType = Field(description='Inclusive start date for generated plans.')
    end_date: DateType = Field(description='Inclusive end date for generated plans.')
    title_prefix: str = Field(default='Content plan', description='Title prefix for generated plans.')
    platform: str = Field(description='Publishing platform or channel.')
    content_type: str = Field(description='Planned content type.')
    goal: str = Field(description='Planning goal or campaign objective.')
    status: str = Field(default='draft', description='Content plan lifecycle status.')

    @model_validator(mode='after')
    def validate_generation_requirements(self) -> 'ContentPlanGenerate':
        if requires_product_id(self.scope) and self.product_id is None:
            raise ValueError('product_id is required when scope is product')
        if self.end_date < self.start_date:
            raise ValueError('end_date must be greater than or equal to start_date')
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
