from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.audience_segments import router as audience_segments_router
from app.api.v1.brands import router as brands_router
from app.api.v1.briefs import router as briefs_router
from app.api.v1.content_items import router as content_items_router
from app.api.v1.content_plans import router as content_plans_router
from app.api.v1.content_versions import router as content_versions_router
from app.api.v1.exports import router as exports_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.media_assets import router as media_assets_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.products import router as products_router
from app.api.v1.quality_checks import router as quality_checks_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.support import router as support_router
from app.api.v1.tickets import router as tickets_router
from app.core.config import settings

app = FastAPI(title="Content Factory API", version="0.3.0")

cors_allowed_origins = list(
    dict.fromkeys(
        [
            settings.cf_app_url.rstrip('/'),
            'http://localhost:3100',
            'http://127.0.0.1:3100',
            'https://app.uno-ai.pw',
        ]
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(organizations_router, prefix="/api/v1")
app.include_router(brands_router, prefix="/api/v1")
app.include_router(briefs_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(media_assets_router, prefix="/api/v1")
app.include_router(audience_segments_router, prefix="/api/v1")
app.include_router(content_plans_router, prefix="/api/v1")
app.include_router(exports_router, prefix="/api/v1")
app.include_router(content_items_router, prefix="/api/v1")
app.include_router(content_versions_router, prefix="/api/v1")
app.include_router(subscriptions_router, prefix="/api/v1")
app.include_router(support_router, prefix="/api/v1")
app.include_router(tickets_router, prefix="/api/v1")
app.include_router(quality_checks_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"service": "cf-api", "status": "ok", "version": "0.3.0"}
