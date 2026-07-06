from datetime import date

from app.core.security import hash_password
from app.db.enums import GenerationType
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.content_version import ContentVersion
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
from app.db.models.user import User
from app.db.session import SessionLocal


def seed_user(email: str, password: str = 'test12345', full_name: str | None = None) -> User:
    db = SessionLocal()
    user = User(
        email=email,
        full_name=full_name or email.split('@')[0].title(),
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers(client, email: str, password: str = 'test12345') -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def seed_review_fixture(paused: bool = False):
    owner = seed_user('owner-p193@example.com')
    reviewer = seed_user('reviewer-p193@example.com')
    outsider = seed_user('outsider-p193@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet193',
        slug='uno-packet193',
        status=OrganizationStatus.PAUSED if paused else OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p193')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-193-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for tickets.',
    )
    db.add(product)
    db.flush()
    content_plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        audience_segment_id=None,
        scope='product',
        date=date(2026, 7, 5),
        title='Rocket Tea review week',
        platform='instagram',
        content_type='post',
        goal='Drive launch awareness',
        status='draft',
    )
    db.add(content_plan)
    db.flush()
    content_item = ContentItem(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        content_plan_id=content_plan.id,
        current_version_id=None,
        title='Review post',
        content_type='post',
        platform='instagram',
        goal='Drive launch awareness',
        status='draft',
    )
    db.add(content_item)
    db.flush()
    version = ContentVersion(
        organization_id=org.id,
        content_item_id=content_item.id,
        version_number=1,
        body_markdown='# Review post\n\nDraft body.',
        structured_json={'headline': 'Draft body'},
        change_summary='Initial draft',
        generation_type=GenerationType.INITIAL,
        generated_from_task_id=None,
        created_by=owner.id,
        is_current=True,
    )
    db.add(version)
    db.flush()
    content_item.current_version_id = version.id
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(product)
    db.refresh(content_plan)
    db.refresh(content_item)
    db.refresh(version)
    org_id = str(org.id)
    db.close()
    return owner, reviewer, outsider, org_id, content_item, version


def test_paused_organization_blocks_review_actions(client):
    owner, _, _, org_id, content_item, _ = seed_review_fixture(paused=True)

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/approve',
        json={'comment': 'Looks fine.'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Paused organization is read-only for content writes'
