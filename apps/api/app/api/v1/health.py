from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "cf-api"}


@router.get("/ready")
async def ready():
    return {"status": "ready", "service": "cf-api"}
