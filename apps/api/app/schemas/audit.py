from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: UUID
    actor_user_id: UUID
    organization_id: UUID | None
    action: str
    entity_type: str
    entity_id: str
    metadata_json: dict[str, object] | None
    ip: str | None
    created_at: datetime
    updated_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
