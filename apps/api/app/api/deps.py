from uuid import UUID

from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.models.organization import MembershipRole, OrganizationMembership
from app.db.models.user import PlatformRole, User
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)
MANAGER_ROLES = {MembershipRole.CLIENT_OWNER, MembershipRole.CLIENT_MANAGER}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def get_accessible_memberships(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrganizationMembership]:
    memberships = db.execute(
        select(OrganizationMembership).where(OrganizationMembership.user_id == current_user.id)
    ).scalars().all()
    if current_user.platform_role in {PlatformRole.SUPER_ADMIN, PlatformRole.PLATFORM_ADMIN}:
        return memberships
    return memberships


def require_organization_membership(
    organization_id: UUID = Query(...),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
) -> OrganizationMembership:
    for membership in memberships:
        if membership.organization_id == organization_id:
            return membership
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to organization")


def get_organization_membership(
    organization_id: UUID,
    memberships: list[OrganizationMembership],
) -> OrganizationMembership:
    for membership in memberships:
        if membership.organization_id == organization_id:
            return membership
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to organization")


def require_organization_manager(
    organization_id: UUID,
    memberships: list[OrganizationMembership],
) -> OrganizationMembership:
    membership = get_organization_membership(organization_id, memberships)
    if membership.role in MANAGER_ROLES:
        return membership
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager access required")


def require_worker_token(x_worker_token: str | None = Header(default=None)) -> str:
    if x_worker_token != settings.worker_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid worker token")
    return x_worker_token


def require_worker_context(
    _worker_token: str = Depends(require_worker_token),
    x_worker_id: str | None = Header(default=None),
) -> str:
    return x_worker_id or "default-worker"
