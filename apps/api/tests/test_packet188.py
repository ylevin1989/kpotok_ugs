from datetime import date

from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
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


def seed_paused_content_version_fixture():
    owner = seed_user('owner-p188@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet188', slug='uno-packet188', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 188', slug='rocket-tea-p188')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-188-001',
        name='Rocket Tea Starter Kit 188',
        category='starter-kit',
        description='Starter kit for paused content-version regression.',
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
        title='Rocket Tea launch week 188',
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
        title='Launch post 188',
        content_type='post',
        platform='instagram',
        goal='Drive launch awareness',
        status='draft',
    )
    db.add(content_item)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    org_id = str(org.id)
    content_item_id = str(content_item.id)
    db.close()
    return owner, org_id, content_item_id


def test_paused_organization_blocks_content_version_creation(client):
    owner, org_id, content_item_id = seed_paused_content_version_fixture()

    paused = client.patch(
        f'/api/v1/organizations/{org_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    response = client.post(
        '/api/v1/content-versions',
        json={
            'organization_id': org_id,
            'content_item_id': content_item_id,
            'version_number': 1,
            'body_markdown': '# Paused content version',
            'structured_json': {'headline': 'Paused'},
            'change_summary': 'Should fail while org is paused',
            'generation_type': 'initial',
            'is_current': True,
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Paused organization is read-only for content writes'
