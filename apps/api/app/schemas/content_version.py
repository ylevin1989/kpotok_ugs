from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.db.enums import GenerationType


class ContentVersionCreate(BaseModel):
    organization_id: UUID = Field(description='Organization that owns the content version.')
    content_item_id: UUID = Field(description='Parent content item.')
    version_number: int = Field(gt=0, description='Monotonic version number for the item.')
    body_markdown: str | None = Field(default=None, description='Markdown body for the version.')
    structured_json: dict | None = Field(default=None, description='Structured payload for renderers.')
    change_summary: str | None = Field(default=None, description='Human-readable change summary.')
    generation_type: GenerationType = Field(default=GenerationType.INITIAL, description='How the version was produced.')
    generated_from_task_id: UUID | None = Field(default=None, description='Optional Hermes task that produced the version.')
    is_current: bool = Field(default=True, description='Whether this version is the current active version.')


class ContentVersionRead(BaseModel):
    id: UUID
    organization_id: UUID
    content_item_id: UUID
    version_number: int
    body_markdown: str | None
    structured_json: dict | None
    change_summary: str | None
    generation_type: GenerationType
    generated_from_task_id: UUID | None
    created_by: UUID | None
    is_current: bool
    created_at: datetime
    updated_at: datetime


class ContentVersionListResponse(BaseModel):
    items: list[ContentVersionRead]
