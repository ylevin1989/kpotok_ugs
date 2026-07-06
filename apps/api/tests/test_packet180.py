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


def seed_content_version_fixture(archived: bool = False):
    owner = seed_user('owner-p180@example.com')
    reviewer = seed_user('reviewer-p180@example.com')
    outsider = seed_user('outsider-p180@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet180',
        slug='uno-packet180',
        status=OrganizationStatus.ARCHIVED if archived else OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p180')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-180-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for version promotion.',
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
        title='Rocket Tea launch week',
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
        title='Launch post',
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
    v1_id = str(v1.id)
    v2_id = str(v2.id)
    content_item_id = str(content_item.id)
    org_id = str(org.id)
    db.close()
    return owner, reviewer, outsider, org_id, content_item_id, v1_id, v2_id


def test_manager_can_promote_existing_content_version_to_current(client):
    owner, reviewer, _, org_id, content_item_id, v1_id, v2_id = seed_content_version_fixture()

    response = client.post(f'/api/v1/content-versions/{v2_id}/promote', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    promoted = response.json()
    assert promoted['id'] == v2_id
    assert promoted['is_current'] is True

    first_response = client.get(f'/api/v1/content-versions/{v1_id}', headers=auth_headers(client, reviewer.email))
    assert first_response.status_code == 200
    assert first_response.json()['is_current'] is False

    item_response = client.get(f'/api/v1/content-items/{content_item_id}', headers=auth_headers(client, reviewer.email))
    assert item_response.status_code == 200
    item = item_response.json()
    assert item['current_version_id'] == v2_id
    assert item['status'] == 'draft'

    list_response = client.get(
        f'/api/v1/content-versions?organization_id={org_id}&content_item_id={content_item_id}',
        headers=auth_headers(client, reviewer.email),
    )
    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert [item['id'] for item in items] == [v1_id, v2_id]
    assert items[1]['is_current'] is True


def test_outsider_cannot_promote_content_version(client):
    _, _, outsider, _, _, _, v2_id = seed_content_version_fixture()

    response = client.post(f'/api/v1/content-versions/{v2_id}/promote', headers=auth_headers(client, outsider.email))
    assert response.status_code == 403


def test_archived_organization_blocks_content_version_promotion(client):
    owner, _, _, _, _, _, v2_id = seed_content_version_fixture(archived=True)

    response = client.post(f'/api/v1/content-versions/{v2_id}/promote', headers=auth_headers(client, owner.email))
    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'
