from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models.organization import MembershipRole, OrganizationStatus
from app.schemas.auth import UserRead


class SupportMembershipRead(BaseModel):
    organization_id: UUID
    organization_name: str
    organization_slug: str
    organization_status: OrganizationStatus
    role: MembershipRole
    created_at: datetime


class SupportUserLookupResponse(BaseModel):
    user: UserRead
    memberships: list[SupportMembershipRead]
