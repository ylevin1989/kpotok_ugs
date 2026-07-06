from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.content_scope import ContentScope, requires_product_id


class GenerationScope(BaseModel):
    scope: ContentScope = Field(description='Generation scope selector for content and AI jobs.')
    product_id: UUID | None = Field(default=None, description='Required when scope is product.')

    @model_validator(mode='after')
    def validate_scope_requirements(self) -> 'GenerationScope':
        if requires_product_id(self.scope) and self.product_id is None:
            raise ValueError('product_id is required when scope is product')
        return self
