from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_current_user, get_organization_membership, require_organization_manager
from app.db.enums import GenerationType
from app.db.models.content_item import ContentItem
from app.db.models.content_version import ContentVersion
from app.db.models.organization import Organization, OrganizationMembership
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.content_version import ContentVersionCreate, ContentVersionListResponse, ContentVersionRead
from app.api.v1.organizations import ensure_content_organization_writable

router = APIRouter(prefix="/content-versions", tags=["content-versions"])


def create_content_version_record(
    *,
    db: Session,
    content_item: ContentItem,
    organization_id: UUID,
    version_number: int,
    body_markdown: str | None,
    structured_json: dict | None,
    change_summary: str | None,
    generation_type: GenerationType,
    generated_from_task_id: UUID | None,
    created_by: UUID | None,
    is_current: bool,
) -> ContentVersion:
    if is_current:
        db.query(ContentVersion).filter(
            ContentVersion.organization_id == organization_id,
            ContentVersion.content_item_id == content_item.id,
            ContentVersion.is_current.is_(True),
        ).update({ContentVersion.is_current: False}, synchronize_session=False)
    content_version = ContentVersion(
        organization_id=organization_id,
        content_item_id=content_item.id,
        version_number=version_number,
        body_markdown=body_markdown,
        structured_json=structured_json,
        change_summary=change_summary,
        generation_type=generation_type,
        generated_from_task_id=generated_from_task_id,
        created_by=created_by,
        is_current=is_current,
    )
    db.add(content_version)
    db.flush()
    if is_current:
        content_item.current_version_id = content_version.id
    return content_version


def next_content_version_number(db: Session, content_item_id: UUID) -> int:
    latest_version_number = db.query(ContentVersion.version_number).filter(
        ContentVersion.content_item_id == content_item_id,
    ).order_by(ContentVersion.version_number.desc()).scalar()
    return (latest_version_number or 0) + 1


def get_content_item_in_organization(db: Session, content_item_id: UUID, organization_id: UUID) -> ContentItem:
    content_item = db.get(ContentItem, content_item_id)
    if content_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found")
    if content_item.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Content item does not belong to organization")
    return content_item


@router.get("", response_model=ContentVersionListResponse)
def list_content_versions(
    organization_id: UUID = Query(...),
    content_item_id: UUID | None = Query(default=None),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ContentVersionListResponse:
    get_organization_membership(organization_id, memberships)
    query = select(ContentVersion).where(ContentVersion.organization_id == organization_id)
    if content_item_id is not None:
        query = query.where(ContentVersion.content_item_id == content_item_id)
    items = db.execute(query.order_by(ContentVersion.version_number.asc(), ContentVersion.created_at.asc())).scalars().all()
    return ContentVersionListResponse(items=[ContentVersionRead.model_validate(item, from_attributes=True) for item in items])


@router.post("", response_model=ContentVersionRead, status_code=status.HTTP_201_CREATED)
def create_content_version(
    payload: ContentVersionCreate,
    current_user: User = Depends(get_current_user),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ContentVersionRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    content_item = get_content_item_in_organization(db, payload.content_item_id, payload.organization_id)
    existing = db.execute(
        select(ContentVersion).where(
            ContentVersion.organization_id == payload.organization_id,
            ContentVersion.content_item_id == payload.content_item_id,
            ContentVersion.version_number == payload.version_number,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Version number already exists for this content item")
    content_version = create_content_version_record(
        db=db,
        content_item=content_item,
        organization_id=payload.organization_id,
        version_number=payload.version_number,
        body_markdown=payload.body_markdown,
        structured_json=payload.structured_json,
        change_summary=payload.change_summary,
        generation_type=payload.generation_type,
        generated_from_task_id=payload.generated_from_task_id,
        created_by=current_user.id,
        is_current=payload.is_current,
    )
    db.commit()
    db.refresh(content_version)
    db.refresh(content_item)
    return ContentVersionRead.model_validate(content_version, from_attributes=True)


@router.post("/{content_version_id}/promote", response_model=ContentVersionRead)
def promote_content_version(
    content_version_id: UUID,
    current_user: User = Depends(get_current_user),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ContentVersionRead:
    content_version = db.get(ContentVersion, content_version_id)
    if content_version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content version not found")
    require_organization_manager(content_version.organization_id, memberships)
    organization = db.get(Organization, content_version.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    content_item = get_content_item_in_organization(db, content_version.content_item_id, content_version.organization_id)
    if not content_version.is_current:
        db.query(ContentVersion).filter(
            ContentVersion.organization_id == content_version.organization_id,
            ContentVersion.content_item_id == content_item.id,
            ContentVersion.is_current.is_(True),
        ).update({ContentVersion.is_current: False}, synchronize_session=False)
        content_version.is_current = True
        content_item.current_version_id = content_version.id
    elif content_item.current_version_id != content_version.id:
        content_item.current_version_id = content_version.id
    db.commit()
    db.refresh(content_version)
    db.refresh(content_item)
    return ContentVersionRead.model_validate(content_version, from_attributes=True)


@router.get("/{content_version_id}", response_model=ContentVersionRead)
def get_content_version(
    content_version_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ContentVersionRead:
    content_version = db.get(ContentVersion, content_version_id)
    if content_version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content version not found")
    get_organization_membership(content_version.organization_id, memberships)
    return ContentVersionRead.model_validate(content_version, from_attributes=True)
