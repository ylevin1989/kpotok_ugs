from typing import Any

from pydantic import BaseModel


class JobHeartbeatRequest(BaseModel):
    stage_name: str | None = None
    stage_label: str | None = None
    progress_percent: int | None = None
    progress_message: str | None = None
    transition_tag: str | None = None
    worker_metadata: dict[str, Any] | None = None


class JobFailureRequest(BaseModel):
    error_message: str


class JobCompleteRequest(BaseModel):
    output_text: str | None = None
    output_artifact_key: str | None = None
    output_artifact_url: str | None = None
    output_artifact_content_type: str | None = None
    output_artifact_size_bytes: int | None = None
    output_artifact_etag: str | None = None
