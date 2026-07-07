from fastapi import HTTPException, status

from app.db.models.brand import Brand, BrandStatus


def ensure_brand_writable(brand: Brand) -> None:
    if brand.status == BrandStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived brand is read-only")


def ensure_brand_content_writable(brand: Brand) -> None:
    if brand.status == BrandStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived brand is read-only for content writes")
    if brand.status == BrandStatus.PAUSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Paused brand is read-only for content writes")


def ensure_archived_brand_transition_allowed(brand: Brand, updates: dict) -> None:
    if brand.status != BrandStatus.ARCHIVED:
        return
    if set(updates.keys()) != {'status'}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived brand is read-only")
    if updates['status'] == BrandStatus.ARCHIVED:
        return
