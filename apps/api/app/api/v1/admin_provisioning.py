from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_platform_admin
from app.db.models.brand import Brand
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership
from app.db.models.product import Product
from app.db.models.user import PlatformRole, User
from app.db.session import get_db

router = APIRouter(prefix='/admin', tags=['admin'])


# ---------- request models ----------
class AdminOrgCreate(BaseModel):
    name: str
    slug: str
    owner_email: str


class AdminBrandCreate(BaseModel):
    organization_id: UUID
    name: str
    slug: str


class AdminMemberAdd(BaseModel):
    organization_id: UUID
    user_email: str
    role: str = 'client_manager'


class AdminRoleSet(BaseModel):
    platform_role: str | None = None


def _user_by_email(db: Session, email: str) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'User not found: {email}')
    return user


# ---------- overview ----------
@router.get('/overview')
def admin_overview(admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)) -> dict:
    return {
        'organizations': db.scalar(select(func.count(Organization.id))) or 0,
        'brands': db.scalar(select(func.count(Brand.id))) or 0,
        'products': db.scalar(select(func.count(Product.id))) or 0,
        'users': db.scalar(select(func.count(User.id))) or 0,
    }


# ---------- read all (platform-wide) ----------
@router.get('/organizations')
def admin_list_organizations(admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)) -> dict:
    orgs = db.execute(select(Organization).order_by(Organization.created_at.desc())).scalars().all()
    items = []
    for o in orgs:
        brands = db.scalar(select(func.count(Brand.id)).where(Brand.organization_id == o.id)) or 0
        products = db.scalar(select(func.count(Product.id)).where(Product.organization_id == o.id)) or 0
        members = db.scalar(select(func.count(OrganizationMembership.id)).where(OrganizationMembership.organization_id == o.id)) or 0
        owner_rows = db.execute(
            select(User.email).join(OrganizationMembership, OrganizationMembership.user_id == User.id)
            .where(OrganizationMembership.organization_id == o.id, OrganizationMembership.role == MembershipRole.CLIENT_OWNER)
        ).scalars().all()
        items.append({
            'id': str(o.id), 'name': o.name, 'slug': o.slug, 'status': o.status.value if hasattr(o.status, 'value') else str(o.status),
            'brands': brands, 'products': products, 'members': members, 'owners': list(owner_rows),
            'created_at': o.created_at.isoformat() if o.created_at else None,
        })
    return {'items': items}


@router.get('/users')
def admin_list_users(admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)) -> dict:
    users = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
    items = []
    for u in users:
        memberships = db.scalar(select(func.count(OrganizationMembership.id)).where(OrganizationMembership.user_id == u.id)) or 0
        items.append({
            'id': str(u.id), 'email': u.email, 'full_name': u.full_name,
            'platform_role': u.platform_role.value if u.platform_role else None,
            'is_active': u.is_active, 'organizations': memberships,
            'created_at': u.created_at.isoformat() if u.created_at else None,
        })
    return {'items': items}


# ---------- provisioning ----------
@router.post('/organizations', status_code=status.HTTP_201_CREATED)
def admin_create_organization(payload: AdminOrgCreate, admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)) -> dict:
    owner = _user_by_email(db, payload.owner_email)
    org = Organization(name=payload.name, slug=payload.slug)
    db.add(org)
    try:
        db.flush()
        db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Organization slug already exists') from exc
    db.refresh(org)
    return {'id': str(org.id), 'name': org.name, 'slug': org.slug, 'owner_email': owner.email}


@router.post('/brands', status_code=status.HTTP_201_CREATED)
def admin_create_brand(payload: AdminBrandCreate, admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)) -> dict:
    org = db.get(Organization, payload.organization_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found')
    brand = Brand(organization_id=org.id, name=payload.name, slug=payload.slug)
    db.add(brand)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Brand slug already exists in this organization') from exc
    db.refresh(brand)
    return {'id': str(brand.id), 'organization_id': str(org.id), 'name': brand.name, 'slug': brand.slug}


@router.post('/memberships', status_code=status.HTTP_201_CREATED)
def admin_add_member(payload: AdminMemberAdd, admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)) -> dict:
    org = db.get(Organization, payload.organization_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found')
    user = _user_by_email(db, payload.user_email)
    try:
        role = MembershipRole(payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Invalid role') from exc
    db.add(OrganizationMembership(organization_id=org.id, user_id=user.id, role=role))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='User is already a member of this organization') from exc
    return {'organization_id': str(org.id), 'user_email': user.email, 'role': role.value}


@router.post('/users/{user_id}/platform-role')
def admin_set_platform_role(user_id: UUID, payload: AdminRoleSet, admin: User = Depends(require_platform_admin), db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    if payload.platform_role is None:
        user.platform_role = None
    else:
        try:
            user.platform_role = PlatformRole(payload.platform_role)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Invalid platform role') from exc
    db.commit()
    return {'id': str(user.id), 'email': user.email, 'platform_role': user.platform_role.value if user.platform_role else None}
