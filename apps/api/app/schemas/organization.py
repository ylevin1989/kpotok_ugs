from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models.organization import MembershipRole, OrganizationStatus


class OrganizationCreate(BaseModel):
    name: str
    slug: str


class OrganizationUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    status: OrganizationStatus | None = None


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    slug: str
    status: OrganizationStatus
    membership_role: MembershipRole
    created_at: datetime
    updated_at: datetime


class OrganizationListResponse(BaseModel):
    items: list[OrganizationRead]


class OrganizationMemberRead(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    full_name: str | None
    role: MembershipRole
    created_at: datetime


class OrganizationMemberListResponse(BaseModel):
    items: list[OrganizationMemberRead]


class OrganizationMemberCreate(BaseModel):
    email: str
    role: MembershipRole


class OrganizationMemberUpdate(BaseModel):
    role: MembershipRole


class OrganizationPermissionEventRead(BaseModel):
    id: UUID
    organization_id: UUID
    actor_user_id: UUID
    actor_membership_role: MembershipRole
    action: str
    target_type: str
    target_id: str
    details: dict[str, object] | None
    created_at: datetime


class OrganizationPermissionEventListResponse(BaseModel):
    items: list[OrganizationPermissionEventRead]
