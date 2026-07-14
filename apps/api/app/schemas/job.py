from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    organization_id: UUID = Field(description='Organization that owns the job.')
    brand_id: UUID = Field(description='Brand scope for the job.')
    brief_id: UUID = Field(description='Source brief that the job should execute from.')
    title: str = Field(description='Human-readable job title.')
    kind: str | None = Field(
        default=None,
        description='Optional explicit job kind. Defaults to manual for legacy generic jobs.',
    )
    target_brand_id: UUID | None = Field(default=None, description='Optional target brand for typed routing.')
    target_product_id: UUID | None = Field(default=None, description='Optional target product for typed routing.')
    target_content_item_id: UUID | None = Field(default=None, description='Optional target content item for typed routing.')
    target_ticket_id: UUID | None = Field(default=None, description='Optional target ticket for typed routing.')
    execution_profile: str | None = Field(
        default=None,
        description='Optional internal execution profile. Defaults to general_content when omitted.',
    )


class JobScope(BaseModel):
    organization_id: UUID
    brand_id: UUID
    brief_id: UUID


class JobExecutionTrace(BaseModel):
    scope: JobScope
    stage_history: list[str]
    stage_timings: list[dict[str, Any]]
    events: list[dict[str, Any]]
    artifact_scope_status: str | None = None
    final_status: str | None = None
    failure_reason: str | None = None
    failure_stage: str | None = None
    failure_code: str | None = None
    validation_result: dict[str, Any] | None = None
    last_progress: dict[str, Any] | None = None
    progress_history: list[dict[str, Any]]
    stage_transition_counts: dict[str, int]
    dominant_stage_name: str | None = None
    stage_duration_ranking: list[dict[str, Any]] = []
    heartbeat_cadence_summary: dict[str, Any] | None = None
    reclaim_continuity: dict[str, Any] | None = None
    progress_extrema: dict[str, Any] | None = None
    retry_profile: dict[str, Any] | None = None
    worker_history: list[str] = []
    transition_tag_rollup: list[str] = []
    transition_tag_counts: dict[str, int] = {}
    unique_transition_tag_count: int = 0
    progress_history_sample_count: int = 0
    worker_metadata_key_summary: list[str] = []
    latest_worker_metadata: dict[str, Any] | None = None
    stage_label_summary: dict[str, str] = {}
    stage_label_history: dict[str, list[str]] = {}
    trace_compact_summary: dict[str, Any] | None = None
    attempt_summary: dict[str, Any] | None = None
    retry_reason: str | None = None


class InternalRolePlanItem(BaseModel):
    role_id: str = Field(description='Stable internal role identifier used by worker execution.')
    label: str = Field(description='Human-readable role label.')
    purpose: str = Field(description='Role purpose used to steer the LLM prompt.')


class JobRead(BaseModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    brief_id: UUID
    brief_content: str | None = None
    context: dict[str, Any] | None = None
    kind: str = Field(description='Explicit job kind used for completion routing.')
    target_brand_id: UUID | None = None
    target_product_id: UUID | None = None
    target_content_item_id: UUID | None = None
    target_ticket_id: UUID | None = None
    scope: JobScope
    execution_profile: str = Field(description='Resolved internal execution profile for the job.')
    internal_role_plan: list[InternalRolePlanItem] = Field(description='Ordered internal role plan resolved for the job.')
    execution_trace: JobExecutionTrace | None = None
    title: str
    status: str
    worker_id: str | None
    attempt_count: int
    lease_expires_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    output_text: str | None
    output_artifact_key: str | None
    output_artifact_url: str | None
    output_artifact_content_type: str | None
    output_artifact_size_bytes: int | None
    output_artifact_etag: str | None
    last_stage: str | None
    last_heartbeat_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    items: list[JobRead]
