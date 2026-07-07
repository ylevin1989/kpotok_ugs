from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_platform_admin
from app.db.models.organization import Organization, OrganizationMembership
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import UserRead
from app.schemas.support import SupportMembershipRead, SupportUserLookupResponse

router = APIRouter(prefix='/support', tags=['support'])


@router.get('/users', response_model=SupportUserLookupResponse)
def lookup_user_by_email(
    email: str = Query(..., min_length=1),
    _current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> SupportUserLookupResponse:
    normalized_email = email.strip().lower()
    user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    membership_rows = db.execute(
        select(OrganizationMembership, Organization)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(OrganizationMembership.user_id == user.id)
        .order_by(Organization.created_at.asc())
    ).all()

    memberships = [
        SupportMembershipRead(
            organization_id=organization.id,
            organization_name=organization.name,
            organization_slug=organization.slug,
            organization_status=organization.status,
            role=membership.role,
            created_at=membership.created_at,
        )
        for membership, organization in membership_rows
    ]

    return SupportUserLookupResponse(user=UserRead.model_validate(user), memberships=memberships)
