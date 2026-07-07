from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models.organization import MembershipRole
from app.db.models.user import PlatformRole


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class UserRead(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    platform_role: PlatformRole | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MembershipRead(BaseModel):
    organization_id: UUID
    role: MembershipRole

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class MeResponse(BaseModel):
    user: UserRead
    memberships: list[MembershipRead]
