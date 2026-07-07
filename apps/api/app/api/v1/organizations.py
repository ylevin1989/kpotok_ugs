import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from uuid import UUID

from app.api.deps import get_accessible_memberships, get_current_user, get_organization_membership, require_organization_manager
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.organization_permission_event import OrganizationPermissionEvent
from app.db.models.user import User
from app.db.session import get_db
from app.domain.audit import record_audit
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationListResponse,
    OrganizationMemberCreate,
    OrganizationMemberListResponse,
    OrganizationMemberRead,
    OrganizationMemberUpdate,
    OrganizationPermissionEventListResponse,
    OrganizationPermissionEventRead,
    OrganizationRead,
    OrganizationUpdate,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _request_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get('x-forwarded-for')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    if request.client is not None:
        return request.client.host
    return None

MEMBERSHIP_CREATE_ROLE_MATRIX: dict[MembershipRole, set[MembershipRole]] = {
    MembershipRole.CLIENT_OWNER: {
        MembershipRole.CLIENT_OWNER,
        MembershipRole.CLIENT_MANAGER,
        MembershipRole.CLIENT_REVIEWER,
    },
    MembershipRole.CLIENT_MANAGER: {
        MembershipRole.CLIENT_MANAGER,
        MembershipRole.CLIENT_REVIEWER,
    },
}

MEMBERSHIP_UPDATE_ROLE_MATRIX: dict[MembershipRole, dict[MembershipRole, set[MembershipRole]]] = {
    MembershipRole.CLIENT_OWNER: {
        MembershipRole.CLIENT_OWNER: {
            MembershipRole.CLIENT_OWNER,
            MembershipRole.CLIENT_MANAGER,
            MembershipRole.CLIENT_REVIEWER,
        },
        MembershipRole.CLIENT_MANAGER: {
            MembershipRole.CLIENT_OWNER,
            MembershipRole.CLIENT_MANAGER,
            MembershipRole.CLIENT_REVIEWER,
        },
        MembershipRole.CLIENT_REVIEWER: {
            MembershipRole.CLIENT_OWNER,
            MembershipRole.CLIENT_MANAGER,
            MembershipRole.CLIENT_REVIEWER,
        },
    },
    MembershipRole.CLIENT_MANAGER: {
        MembershipRole.CLIENT_MANAGER: {
            MembershipRole.CLIENT_MANAGER,
            MembershipRole.CLIENT_REVIEWER,
        },
        MembershipRole.CLIENT_REVIEWER: {
            MembershipRole.CLIENT_MANAGER,
            MembershipRole.CLIENT_REVIEWER,
        },
    },
}

MEMBERSHIP_DELETE_ROLE_MATRIX: dict[MembershipRole, set[MembershipRole]] = {
    MembershipRole.CLIENT_OWNER: {
        MembershipRole.CLIENT_OWNER,
        MembershipRole.CLIENT_MANAGER,
        MembershipRole.CLIENT_REVIEWER,
    },
    MembershipRole.CLIENT_MANAGER: {
        MembershipRole.CLIENT_MANAGER,
        MembershipRole.CLIENT_REVIEWER,
    },
}


@router.get("", response_model=OrganizationListResponse)
def list_organizations(
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> OrganizationListResponse:
    if not memberships:
        return OrganizationListResponse(items=[])
    organization_ids = [membership.organization_id for membership in memberships]
    organizations = db.execute(
        select(Organization).where(Organization.id.in_(organization_ids)).order_by(Organization.created_at.asc())
    ).scalars().all()
    role_map = {membership.organization_id: membership.role for membership in memberships}
    items = [
        OrganizationRead(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            status=organization.status,
            membership_role=role_map[organization.id],
            created_at=organization.created_at,
            updated_at=organization.updated_at,
        )
        for organization in organizations
    ]
    return OrganizationListResponse(items=items)


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationRead:
    organization = Organization(name=payload.name, slug=payload.slug)
    db.add(organization)
    try:
        db.flush()
        membership = OrganizationMembership(
            organization_id=organization.id,
            user_id=current_user.id,
            role=MembershipRole.CLIENT_OWNER,
        )
        db.add(membership)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization slug already exists") from exc
    db.refresh(organization)
    return OrganizationRead(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        status=organization.status,
        membership_role=MembershipRole.CLIENT_OWNER,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
    )


@router.get("/{organization_id}", response_model=OrganizationRead)
def get_organization(
    organization_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> OrganizationRead:
    membership = get_organization_membership(organization_id, memberships)
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationRead(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        status=organization.status,
        membership_role=membership.role,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
    )


@router.patch("/{organization_id}", response_model=OrganizationRead)
def update_organization(
    organization_id: UUID,
    payload: OrganizationUpdate,
    request: Request,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> OrganizationRead:
    membership = require_organization_manager(organization_id, memberships)
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    updates = payload.model_dump(exclude_unset=True)
    ensure_archived_organization_transition_allowed(membership, organization, updates)
    if organization.status != OrganizationStatus.ARCHIVED:
        ensure_organization_writable(organization)
    if 'status' in updates:
        ensure_organization_status_change_allowed(membership, organization, updates['status'])
    old_status = organization.status
    for field, value in updates.items():
        setattr(organization, field, value)
    if 'status' in updates and updates['status'] != old_status:
        _record_permission_event(
            db,
            organization_id=organization_id,
            actor_membership=membership,
            action='organization_status_changed',
            target_type='organization',
            target_id=str(organization_id),
            details={'from': old_status.value, 'to': updates['status'].value},
        )
        record_audit(
            db,
            actor_user_id=membership.user_id,
            organization_id=organization_id,
            action='organization_status_changed',
            entity_type='organization',
            entity_id=str(organization_id),
            metadata={'from': old_status.value, 'to': updates['status'].value},
            ip=_request_ip(request),
        )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization slug already exists") from exc
    db.refresh(organization)
    return OrganizationRead(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        status=organization.status,
        membership_role=membership.role,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
    )


def _member_read(membership: OrganizationMembership, user: User) -> OrganizationMemberRead:
    return OrganizationMemberRead(
        id=membership.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        created_at=membership.created_at,
    )


def _permission_event_read(event: OrganizationPermissionEvent) -> OrganizationPermissionEventRead:
    return OrganizationPermissionEventRead(
        id=event.id,
        organization_id=event.organization_id,
        actor_user_id=event.actor_user_id,
        actor_membership_role=MembershipRole(event.actor_membership_role),
        action=event.action,
        target_type=event.target_type,
        target_id=event.target_id,
        details=json.loads(event.details_json) if event.details_json else None,
        created_at=event.created_at,
    )


def _record_permission_event(
    db: Session,
    *,
    organization_id: UUID,
    actor_membership: OrganizationMembership,
    action: str,
    target_type: str,
    target_id: str,
    details: dict[str, object] | None = None,
) -> None:
    db.add(
        OrganizationPermissionEvent(
            organization_id=organization_id,
            actor_user_id=actor_membership.user_id,
            actor_membership_role=actor_membership.role.value,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details_json=json.dumps(details, sort_keys=True) if details is not None else None,
        )
    )


def ensure_organization_writable(organization: Organization) -> None:
    if organization.status == OrganizationStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived organization is read-only")


def ensure_content_organization_writable(organization: Organization) -> None:
    if organization.status == OrganizationStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived organization is read-only")
    if organization.status == OrganizationStatus.PAUSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Paused organization is read-only for content writes")


def ensure_archived_organization_transition_allowed(
    actor_membership: OrganizationMembership,
    organization: Organization,
    updates: dict,
) -> None:
    if organization.status != OrganizationStatus.ARCHIVED:
        return
    if set(updates.keys()) != {'status'}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived organization is read-only")
    target_status = updates['status']
    if target_status == OrganizationStatus.ARCHIVED:
        return
    if actor_membership.role != MembershipRole.CLIENT_OWNER:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived organization is read-only")


def ensure_organization_status_change_allowed(
    actor_membership: OrganizationMembership,
    organization: Organization,
    target_status: OrganizationStatus,
) -> None:
    if target_status == organization.status:
        return
    if actor_membership.role != MembershipRole.CLIENT_OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owners can change organization status")


def ensure_membership_create_role_allowed(actor_membership: OrganizationMembership, target_role: MembershipRole) -> None:
    allowed_roles = MEMBERSHIP_CREATE_ROLE_MATRIX.get(actor_membership.role, set())
    if target_role in allowed_roles:
        return
    if target_role == MembershipRole.CLIENT_OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owners can assign owner role")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role assignment not allowed")


def ensure_membership_update_matrix_allowed(
    actor_membership: OrganizationMembership,
    target_membership: OrganizationMembership,
    target_role: MembershipRole,
) -> None:
    if actor_membership.role != MembershipRole.CLIENT_OWNER and target_membership.role == MembershipRole.CLIENT_OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owners can modify owner memberships")
    allowed_roles = MEMBERSHIP_UPDATE_ROLE_MATRIX.get(actor_membership.role, {}).get(target_membership.role, set())
    if target_role in allowed_roles:
        return
    if target_role == MembershipRole.CLIENT_OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owners can assign owner role")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role transition not allowed")


def ensure_owner_role_change_safe(
    organization_id: UUID,
    target_membership: OrganizationMembership,
    target_role: MembershipRole,
    db: Session,
) -> None:
    if target_membership.role != MembershipRole.CLIENT_OWNER or target_role == MembershipRole.CLIENT_OWNER:
        return
    owner_memberships = db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.role == MembershipRole.CLIENT_OWNER,
        )
    ).scalars().all()
    if len(owner_memberships) <= 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot change the last owner role")


def ensure_membership_role_transition_allowed(
    organization_id: UUID,
    actor_membership: OrganizationMembership,
    target_membership: OrganizationMembership,
    target_role: MembershipRole,
    db: Session,
) -> None:
    ensure_membership_update_matrix_allowed(actor_membership, target_membership, target_role)
    ensure_owner_role_change_safe(organization_id, target_membership, target_role, db)


def ensure_membership_delete_allowed(
    actor_membership: OrganizationMembership,
    target_membership: OrganizationMembership,
) -> None:
    allowed_roles = MEMBERSHIP_DELETE_ROLE_MATRIX.get(actor_membership.role, set())
    if target_membership.role in allowed_roles:
        return
    if target_membership.role == MembershipRole.CLIENT_OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owners can modify owner memberships")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Membership deletion not allowed")


def ensure_owner_membership_delete_safe(organization_id: UUID, target_membership: OrganizationMembership, db: Session) -> None:
    if target_membership.role != MembershipRole.CLIENT_OWNER:
        return
    owner_memberships = db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.role == MembershipRole.CLIENT_OWNER,
        )
    ).scalars().all()
    if len(owner_memberships) <= 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot remove the last owner")


@router.get("/{organization_id}/members", response_model=OrganizationMemberListResponse)
def list_organization_members(
    organization_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> OrganizationMemberListResponse:
    require_organization_manager(organization_id, memberships)
    rows = db.execute(
        select(OrganizationMembership, User)
        .join(User, User.id == OrganizationMembership.user_id)
        .where(OrganizationMembership.organization_id == organization_id)
        .order_by(OrganizationMembership.created_at.asc())
    ).all()
    return OrganizationMemberListResponse(items=[_member_read(membership, user) for membership, user in rows])


@router.post("/{organization_id}/members", response_model=OrganizationMemberRead, status_code=status.HTTP_201_CREATED)
def add_organization_member(
    organization_id: UUID,
    payload: OrganizationMemberCreate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> OrganizationMemberRead:
    actor_membership = require_organization_manager(organization_id, memberships)
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_organization_writable(organization)
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    membership = db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user.id,
        )
    ).scalar_one_or_none()
    if membership is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already belongs to organization")
    ensure_membership_create_role_allowed(actor_membership, payload.role)
    membership = OrganizationMembership(organization_id=organization_id, user_id=user.id, role=payload.role)
    db.add(membership)
    db.flush()
    _record_permission_event(
        db,
        organization_id=organization_id,
        actor_membership=actor_membership,
        action='membership_created',
        target_type='membership',
        target_id=str(membership.id),
        details={'role': payload.role.value, 'email': user.email},
    )
    db.commit()
    db.refresh(membership)
    return _member_read(membership, user)


@router.patch("/{organization_id}/members/{membership_id}", response_model=OrganizationMemberRead)
def update_organization_member(
    organization_id: UUID,
    membership_id: UUID,
    payload: OrganizationMemberUpdate,
    request: Request,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> OrganizationMemberRead:
    actor_membership = require_organization_manager(organization_id, memberships)
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_organization_writable(organization)
    membership = db.get(OrganizationMembership, membership_id)
    if membership is None or membership.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    ensure_membership_role_transition_allowed(organization_id, actor_membership, membership, payload.role, db)
    old_role = membership.role
    membership.role = payload.role
    if old_role != payload.role:
        _record_permission_event(
            db,
            organization_id=organization_id,
            actor_membership=actor_membership,
            action='membership_role_changed',
            target_type='membership',
            target_id=str(membership.id),
            details={'from': old_role.value, 'to': payload.role.value},
        )
        record_audit(
            db,
            actor_user_id=actor_membership.user_id,
            organization_id=organization_id,
            action='organization_member_role_changed',
            entity_type='membership',
            entity_id=str(membership.id),
            metadata={'from': old_role.value, 'to': payload.role.value},
            ip=_request_ip(request),
        )
    db.commit()
    db.refresh(membership)
    user = db.get(User, membership.user_id)
    assert user is not None
    return _member_read(membership, user)


@router.delete("/{organization_id}/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization_member(
    organization_id: UUID,
    membership_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    actor_membership = require_organization_manager(organization_id, memberships)
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_organization_writable(organization)
    membership = db.get(OrganizationMembership, membership_id)
    if membership is None or membership.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    ensure_membership_delete_allowed(actor_membership, membership)
    if membership.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot remove your own membership")
    ensure_owner_membership_delete_safe(organization_id, membership, db)
    _record_permission_event(
        db,
        organization_id=organization_id,
        actor_membership=actor_membership,
        action='membership_deleted',
        target_type='membership',
        target_id=str(membership.id),
        details={'role': membership.role.value},
    )
    db.delete(membership)
    db.commit()


@router.get("/{organization_id}/permission-events", response_model=OrganizationPermissionEventListResponse)
def list_organization_permission_events(
    organization_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> OrganizationPermissionEventListResponse:
    require_organization_manager(organization_id, memberships)
    rows = db.execute(
        select(OrganizationPermissionEvent)
        .where(OrganizationPermissionEvent.organization_id == organization_id)
        .order_by(OrganizationPermissionEvent.created_at.desc(), OrganizationPermissionEvent.id.desc())
    ).scalars().all()
    return OrganizationPermissionEventListResponse(items=[_permission_event_read(event) for event in rows])
