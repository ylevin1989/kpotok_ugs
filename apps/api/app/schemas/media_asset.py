from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.content_scope import ContentScope, requires_product_id


class MediaAssetCreate(BaseModel):
    organization_id: UUID = Field(description='Organization that owns the media asset.')
    brand_id: UUID = Field(description='Brand scope for the media asset.')
    product_id: UUID | None = Field(default=None, description='Required when scope is product.')
    scope: ContentScope = Field(default=ContentScope.BRAND, description='Media asset scope.')
    name: str = Field(description='Human-readable asset name.')
    description: str = Field(description='Canonical asset description.')
    asset_key: str = Field(description='MinIO object key for the asset.')
    source_url: str | None = Field(default=None, description='Optional source URL for the asset.')
    content_type: str = Field(description='MIME type of the asset.')
    size_bytes: int | None = Field(default=None, description='Optional byte size of the asset.')
    checksum: str | None = Field(default=None, description='Optional checksum or ETag.')

    @model_validator(mode='after')
    def validate_scope_requirements(self) -> 'MediaAssetCreate':
        if requires_product_id(self.scope) and self.product_id is None:
            raise ValueError('product_id is required when scope is product')
        return self


class MediaAssetRead(BaseModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    product_id: UUID | None
    scope: ContentScope
    name: str
    description: str
    asset_key: str
    source_url: str | None
    content_type: str
    size_bytes: int | None
    checksum: str | None
    created_at: datetime
    updated_at: datetime


class MediaAssetListResponse(BaseModel):
    items: list[MediaAssetRead]
