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


def seed_content_version_fixture(archived: bool = False):
    owner = seed_user('owner-p166@example.com')
    reviewer = seed_user('reviewer-p166@example.com')
    outsider = seed_user('outsider-p166@example.com')
    other_owner = seed_user('other-owner-p166@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet166',
        slug='uno-packet166',
        status=OrganizationStatus.ARCHIVED if archived else OrganizationStatus.ACTIVE,
    )
    other_org = Organization(name='Other Packet166', slug='other-packet166', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.add(other_org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p166')
    other_brand = Brand(organization_id=other_org.id, name='Other Brand', slug='other-brand-p166')
    db.add(brand)
    db.add(other_brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-166-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for content versions.',
    )
    other_product = Product(
        organization_id=other_org.id,
        brand_id=other_brand.id,
        sku='SKU-OTHER-166',
        name='Other Starter Kit',
        category='starter-kit',
        description='Belongs to another organization.',
    )
    db.add(product)
    db.add(other_product)
    db.flush()
    content_plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        audience_segment_id=None,
        scope='product',
        date=date(2026, 7, 5),
        title='Rocket Tea launch week',
        platform='instagram',
        content_type='post',
        goal='Drive launch awareness',
        status='draft',
    )
    other_content_plan = ContentPlan(
        organization_id=other_org.id,
        brand_id=other_brand.id,
        product_id=other_product.id,
        audience_segment_id=None,
        scope='product',
        date=date(2026, 7, 5),
        title='Other launch week',
        platform='instagram',
        content_type='post',
        goal='Other launch awareness',
        status='draft',
    )
    db.add(content_plan)
    db.add(other_content_plan)
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
    other_content_item = ContentItem(
        organization_id=other_org.id,
        brand_id=other_brand.id,
        product_id=other_product.id,
        content_plan_id=other_content_plan.id,
        current_version_id=None,
        title='Other post',
        content_type='post',
        platform='instagram',
        goal='Belongs to another organization.',
        status='draft',
    )
    db.add(content_item)
    db.add(other_content_item)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.add(OrganizationMembership(organization_id=other_org.id, user_id=other_owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(product)
    db.refresh(content_plan)
    db.refresh(content_item)
    db.refresh(other_org)
    db.refresh(other_brand)
    db.refresh(other_product)
    db.refresh(other_content_item)
    db.close()
    return owner, reviewer, outsider, other_owner, org, brand, product, content_plan, content_item, other_org, other_brand, other_product, other_content_item


def test_manager_can_create_list_and_get_content_versions_and_update_current_version(client):
    owner, reviewer, _, _, org, brand, product, content_plan, content_item, _, _, _, _ = seed_content_version_fixture()

    create_response = client.post(
        '/api/v1/content-versions',
        json={
            'organization_id': str(org.id),
            'content_item_id': str(content_item.id),
            'version_number': 1,
            'body_markdown': '# Launch post\n\nRocket Tea is live.',
            'structured_json': {'headline': 'Rocket Tea is live'},
            'change_summary': 'Initial draft',
            'generation_type': 'initial',
            'is_current': True,
        },
        headers=auth_headers(client, owner.email),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created['organization_id'] == str(org.id)
    assert created['content_item_id'] == str(content_item.id)
    assert created['version_number'] == 1
    assert created['is_current'] is True

    list_response = client.get(
        f'/api/v1/content-versions?organization_id={org.id}&content_item_id={content_item.id}',
        headers=auth_headers(client, reviewer.email),
    )
    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == created['id']
    assert items[0]['generation_type'] == 'initial'

    get_response = client.get(f"/api/v1/content-versions/{created['id']}", headers=auth_headers(client, reviewer.email))
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched['id'] == created['id']
    assert fetched['created_by'] == str(owner.id)

    second_response = client.post(
        '/api/v1/content-versions',
        json={
            'organization_id': str(org.id),
            'content_item_id': str(content_item.id),
            'version_number': 2,
            'body_markdown': '# Launch post\n\nRocket Tea is live. Updated.',
            'structured_json': {'headline': 'Rocket Tea is live', 'variant': 2},
            'change_summary': 'Second draft',
            'generation_type': 'revision',
            'is_current': True,
        },
        headers=auth_headers(client, owner.email),
    )

    assert second_response.status_code == 201
    second = second_response.json()
    assert second['version_number'] == 2
    assert second['is_current'] is True

    refreshed_get = client.get(f"/api/v1/content-versions/{created['id']}", headers=auth_headers(client, reviewer.email))
    assert refreshed_get.status_code == 200
    assert refreshed_get.json()['is_current'] is False

    item_response = client.get(f"/api/v1/content-items/{content_item.id}", headers=auth_headers(client, reviewer.email))
    assert item_response.status_code == 200
    assert item_response.json()['current_version_id'] == second['id']


def test_cannot_create_content_version_with_duplicate_number(client):
    owner, _, _, _, org, _, _, _, content_item, _, _, _, _ = seed_content_version_fixture()

    first = client.post(
        '/api/v1/content-versions',
        json={
            'organization_id': str(org.id),
            'content_item_id': str(content_item.id),
            'version_number': 1,
            'body_markdown': 'v1',
            'structured_json': {'v': 1},
            'change_summary': 'Initial draft',
            'generation_type': 'initial',
            'is_current': True,
        },
        headers=auth_headers(client, owner.email),
    )
    assert first.status_code == 201

    duplicate = client.post(
        '/api/v1/content-versions',
        json={
            'organization_id': str(org.id),
            'content_item_id': str(content_item.id),
            'version_number': 1,
            'body_markdown': 'v1 again',
            'structured_json': {'v': 1},
            'change_summary': 'Duplicate',
            'generation_type': 'revision',
            'is_current': False,
        },
        headers=auth_headers(client, owner.email),
    )

    assert duplicate.status_code == 409
    assert duplicate.json()['detail'] == 'Version number already exists for this content item'


def test_cannot_create_content_version_when_content_item_does_not_belong_to_organization(client):
    owner, _, _, _, org, _, _, _, _, _, _, _, other_content_item = seed_content_version_fixture()

    response = client.post(
        '/api/v1/content-versions',
        json={
            'organization_id': str(org.id),
            'content_item_id': str(other_content_item.id),
            'version_number': 1,
            'body_markdown': 'bad',
            'structured_json': {'bad': True},
            'change_summary': 'Mismatch',
            'generation_type': 'initial',
            'is_current': True,
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Content item does not belong to organization'


def test_archived_organization_blocks_content_version_create(client):
    owner, _, _, _, org, _, _, _, content_item, _, _, _, _ = seed_content_version_fixture(archived=True)

    response = client.post(
        '/api/v1/content-versions',
        json={
            'organization_id': str(org.id),
            'content_item_id': str(content_item.id),
            'version_number': 1,
            'body_markdown': 'bad',
            'structured_json': {'bad': True},
            'change_summary': 'Frozen org',
            'generation_type': 'initial',
            'is_current': True,
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_outsider_cannot_list_content_versions(client):
    _, _, outsider, _, org, _, _, _, content_item, _, _, _, _ = seed_content_version_fixture()

    response = client.get(
        f'/api/v1/content-versions?organization_id={org.id}&content_item_id={content_item.id}',
        headers=auth_headers(client, outsider.email),
    )

    assert response.status_code == 403
