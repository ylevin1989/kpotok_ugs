from datetime import date

from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.content_version import ContentVersion
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
from app.db.models.user import User
from app.db.session import SessionLocal


def seed_user(email: str, password: str = 'test12345') -> User:
    db = SessionLocal()
    user = User(email=email, password_hash=hash_password(password), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers(client, email: str, password: str = 'test12345') -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def seed_content_version_fixture(paused: bool = False):
    owner = seed_user('owner-p194@example.com')
    reviewer = seed_user('reviewer-p194@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet194',
        slug='uno-packet194',
        status=OrganizationStatus.PAUSED if paused else OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 194', slug='rocket-tea-p194')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-194-001',
        name='Rocket Tea Starter Kit 194',
        category='starter-kit',
        description='Starter kit for paused version-promotion regression.',
    )
    db.add(product)
    db.flush()
    content_plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        audience_segment_id=None,
        scope='product',
        date=date(2026, 7, 6),
        title='Rocket Tea launch week 194',
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
        title='Launch post 194',
        content_type='post',
        platform='instagram',
        goal='Drive launch awareness',
        status='draft',
    )
    db.add(content_item)
    db.flush()
    v1 = ContentVersion(
        organization_id=org.id,
        content_item_id=content_item.id,
        version_number=1,
        body_markdown='# Launch post\n\nVersion 1.',
        structured_json={'headline': 'Version 1'},
        change_summary='Initial draft',
        generation_type='initial',
        generated_from_task_id=None,
        created_by=owner.id,
        is_current=True,
    )
    db.add(v1)
    db.flush()
    content_item.current_version_id = v1.id
    v2 = ContentVersion(
        organization_id=org.id,
        content_item_id=content_item.id,
        version_number=2,
        body_markdown='# Launch post\n\nVersion 2.',
        structured_json={'headline': 'Version 2'},
        change_summary='Second draft',
        generation_type='revision',
        generated_from_task_id=None,
        created_by=owner.id,
        is_current=False,
    )
    db.add(v2)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    org_id = str(org.id)
    v2_id = str(v2.id)
    db.close()
    return owner, reviewer, org_id, v2_id


def test_paused_organization_blocks_content_version_promotion(client):
    owner, _, org_id, v2_id = seed_content_version_fixture(paused=True)

    paused = client.patch(
        f'/api/v1/organizations/{org_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    response = client.post(f'/api/v1/content-versions/{v2_id}/promote', headers=auth_headers(client, owner.email))

    assert response.status_code == 409
    assert response.json()['detail'] == 'Paused organization is read-only for content writes'
