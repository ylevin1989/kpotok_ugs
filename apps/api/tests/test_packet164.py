import pytest

from app.core.security import hash_password
from app.db.models.audience_segment import AudienceSegment
from app.db.models.brand import Brand
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


def seed_content_plan_fixture(archived: bool = False):
    owner = seed_user('owner-p164@example.com')
    reviewer = seed_user('reviewer-p164@example.com')
    outsider = seed_user('outsider-p164@example.com')
    other_owner = seed_user('other-owner-p164@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet164',
        slug='uno-packet164',
        status=OrganizationStatus.ARCHIVED if archived else OrganizationStatus.ACTIVE,
    )
    other_org = Organization(name='Other Packet164', slug='other-packet164', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.add(other_org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p164')
    other_brand = Brand(organization_id=other_org.id, name='Other Brand', slug='other-brand-p164')
    db.add(brand)
    db.add(other_brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-164-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for content plans.',
    )
    other_product = Product(
        organization_id=other_org.id,
        brand_id=other_brand.id,
        sku='SKU-OTHER-164',
        name='Other Starter Kit',
        category='starter-kit',
        description='Belongs to another organization.',
    )
    db.add(product)
    db.add(other_product)
    db.flush()
    audience_segment = AudienceSegment(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        scope='product',
        name='Busy decision-maker',
        description='Needs fast proof and low-friction onboarding.',
        pain_points=['Not enough time'],
        goals=['Move fast'],
        objections=['Too complex'],
        keywords=['quick setup'],
    )
    other_audience_segment = AudienceSegment(
        organization_id=other_org.id,
        brand_id=other_brand.id,
        product_id=other_product.id,
        scope='product',
        name='Other segment',
        description='Belongs to another organization.',
        pain_points=['Other'],
        goals=['Other'],
        objections=['Other'],
        keywords=['Other'],
    )
    db.add(audience_segment)
    db.add(other_audience_segment)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.add(OrganizationMembership(organization_id=other_org.id, user_id=other_owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(product)
    db.refresh(audience_segment)
    db.refresh(other_org)
    db.refresh(other_brand)
    db.refresh(other_product)
    db.refresh(other_audience_segment)
    db.close()
    return owner, reviewer, outsider, other_owner, org, brand, product, audience_segment, other_org, other_brand, other_product, other_audience_segment


def test_manager_can_create_list_and_get_content_plans_with_scope_validation(client):
    owner, reviewer, _, _, org, brand, product, audience_segment, _, _, _, _ = seed_content_plan_fixture()

    create_response = client.post(
        '/api/v1/content-plans',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'product_id': str(product.id),
            'audience_segment_id': str(audience_segment.id),
            'scope': 'product',
            'date': '2026-07-05',
            'title': 'Rocket Tea launch week',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Drive launch awareness',
            'status': 'draft',
        },
        headers=auth_headers(client, owner.email),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created['organization_id'] == str(org.id)
    assert created['brand_id'] == str(brand.id)
    assert created['product_id'] == str(product.id)
    assert created['audience_segment_id'] == str(audience_segment.id)
    assert created['scope'] == 'product'
    assert created['title'] == 'Rocket Tea launch week'

    list_response = client.get(
        f'/api/v1/content-plans?organization_id={org.id}&brand_id={brand.id}&scope=product&product_id={product.id}',
        headers=auth_headers(client, reviewer.email),
    )

    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == created['id']
    assert items[0]['platform'] == 'instagram'

    get_response = client.get(f"/api/v1/content-plans/{created['id']}", headers=auth_headers(client, reviewer.email))

    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched['id'] == created['id']
    assert fetched['scope'] == 'product'


def test_cannot_create_content_plan_without_product_id_for_product_scope(client):
    owner, _, _, _, org, brand, _, _, _, _, _, _ = seed_content_plan_fixture()

    response = client.post(
        '/api/v1/content-plans',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'scope': 'product',
            'date': '2026-07-05',
            'title': 'Broken plan',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Should fail',
            'status': 'draft',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 422
    assert 'product_id is required when scope is product' in response.text


def test_cannot_create_content_plan_when_product_does_not_belong_to_brand(client):
    owner, _, _, _, org, brand, _, audience_segment, _, _, other_product, _ = seed_content_plan_fixture()

    response = client.post(
        '/api/v1/content-plans',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'product_id': str(other_product.id),
            'audience_segment_id': str(audience_segment.id),
            'scope': 'product',
            'date': '2026-07-05',
            'title': 'Mismatch plan',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Should fail',
            'status': 'draft',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Product does not belong to organization and brand'


def test_cannot_create_content_plan_when_audience_segment_does_not_belong_to_brand(client):
    owner, _, _, _, org, brand, product, _, _, _, _, other_audience_segment = seed_content_plan_fixture()

    response = client.post(
        '/api/v1/content-plans',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'product_id': str(product.id),
            'audience_segment_id': str(other_audience_segment.id),
            'scope': 'product',
            'date': '2026-07-05',
            'title': 'Mismatch audience plan',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Should fail',
            'status': 'draft',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Audience segment does not belong to organization and brand'


def test_archived_organization_blocks_content_plan_create(client):
    owner, _, _, _, org, brand, _, _, _, _, _, _ = seed_content_plan_fixture(archived=True)

    response = client.post(
        '/api/v1/content-plans',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'scope': 'brand',
            'date': '2026-07-05',
            'title': 'Frozen plan',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Should fail',
            'status': 'draft',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_outsider_cannot_list_content_plans_for_inaccessible_organization(client):
    owner, _, outsider, _, org, brand, product, audience_segment, _, _, _, _ = seed_content_plan_fixture()

    create_response = client.post(
        '/api/v1/content-plans',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'product_id': str(product.id),
            'audience_segment_id': str(audience_segment.id),
            'scope': 'product',
            'date': '2026-07-05',
            'title': 'Visible plan',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Should be hidden from outsider',
            'status': 'draft',
        },
        headers=auth_headers(client, owner.email),
    )
    assert create_response.status_code == 201

    response = client.get(
        f'/api/v1/content-plans?organization_id={org.id}&brand_id={brand.id}',
        headers=auth_headers(client, outsider.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'No access to organization'
