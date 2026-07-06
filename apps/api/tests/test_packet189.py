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


def seed_paused_ticket_fixture():
    owner = seed_user('owner-p189@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet189', slug='uno-packet189', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 189', slug='rocket-tea-p189')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-189-001',
        name='Rocket Tea Starter Kit 189',
        category='starter-kit',
        description='Starter kit for paused ticket regression.',
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
        title='Rocket Tea launch week 189',
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
        title='Launch post 189',
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
        body_markdown='# Launch post 189',
        structured_json={'headline': 'Launch post 189'},
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
    db.commit()
    org_id = str(org.id)
    brand_id = str(brand.id)
    product_id = str(product.id)
    content_item_id = str(content_item.id)
    version_id = str(version.id)
    db.close()
    return owner, org_id, brand_id, product_id, content_item_id, version_id


def test_paused_organization_blocks_ticket_creation(client):
    owner, org_id, brand_id, product_id, content_item_id, version_id = seed_paused_ticket_fixture()

    paused = client.patch(
        f'/api/v1/organizations/{org_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    response = client.post(
        '/api/v1/tickets',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'product_id': product_id,
            'content_item_id': content_item_id,
            'content_version_id': version_id,
            'type': 'approval',
            'reason_codes': ['ready_to_publish'],
            'comment': 'Should fail while org is paused',
            'priority': 'normal',
            'assigned_agent_role': 'reviewer',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Paused organization is read-only for content writes'
