from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.enums import ExportFormat, ExportStatus
from app.domain.content_scope import ContentScope


class ExportCreate(BaseModel):
    organization_id: UUID = Field(description='Organization that owns the export.')
    brand_id: UUID = Field(description='Brand scope for the export.')
    content_plan_id: UUID | None = Field(default=None, description='Optional content-plan scope for the export.')
    scope: ContentScope | None = Field(default=None, description='Optional content scope filter.')
    product_id: UUID | None = Field(default=None, description='Optional product filter.')
    audience_segment_id: UUID | None = Field(default=None, description='Optional audience segment filter.')
    format: ExportFormat = Field(description='Export artifact format.')


class ContentPlanExportCreate(BaseModel):
    format: ExportFormat = Field(description='Export artifact format.')


class ExportRead(BaseModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    content_plan_id: UUID | None
    format: ExportFormat
    status: ExportStatus
    filter_json: dict[str, Any] | None
    file_key: str | None
    file_size_bytes: int | None
    content_type: str | None
    error_message: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class ExportListResponse(BaseModel):
    items: list[ExportRead]


class LegacyContentPlanExport(BaseModel):
    organization_id: UUID = Field(description='Organization that owns the exported content plans.')
    brand_id: UUID = Field(description='Brand scope for the exported content plans.')
    scope: ContentScope | None = Field(default=None, description='Optional content plan scope filter.')
    product_id: UUID | None = Field(default=None, description='Optional product filter.')
    audience_segment_id: UUID | None = Field(default=None, description='Optional audience segment filter.')
    format: Literal['csv', 'json'] = Field(default='csv', description='Legacy inline export format.')
