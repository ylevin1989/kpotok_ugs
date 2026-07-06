from datetime import date

from app.core.security import hash_password
from app.db.models.audience_segment import AudienceSegment
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


def seed_content_item_fixture(archived: bool = False):
    owner = seed_user('owner-p165@example.com')
    reviewer = seed_user('reviewer-p165@example.com')
    outsider = seed_user('outsider-p165@example.com')
    other_owner = seed_user('other-owner-p165@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet165',
        slug='uno-packet165',
        status=OrganizationStatus.ARCHIVED if archived else OrganizationStatus.ACTIVE,
    )
    other_org = Organization(name='Other Packet165', slug='other-packet165', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.add(other_org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p165')
    other_brand = Brand(organization_id=other_org.id, name='Other Brand', slug='other-brand-p165')
    db.add(brand)
    db.add(other_brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-165-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for content items.',
    )
    other_product = Product(
        organization_id=other_org.id,
        brand_id=other_brand.id,
        sku='SKU-OTHER-165',
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
    plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        audience_segment_id=audience_segment.id,
        scope='product',
        date=date(2026, 7, 5),
        title='Rocket Tea launch week',
        platform='instagram',
        content_type='post',
        goal='Drive launch awareness',
        status='draft',
    )
    other_plan = ContentPlan(
        organization_id=other_org.id,
        brand_id=other_brand.id,
        product_id=other_product.id,
        audience_segment_id=other_audience_segment.id,
        scope='product',
        date=date(2026, 7, 5),
        title='Other launch week',
        platform='instagram',
        content_type='post',
        goal='Drive awareness elsewhere',
        status='draft',
    )
    db.add(plan)
    db.add(other_plan)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.add(OrganizationMembership(organization_id=other_org.id, user_id=other_owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(product)
    db.refresh(audience_segment)
    db.refresh(plan)
    db.refresh(other_org)
    db.refresh(other_brand)
    db.refresh(other_product)
    db.refresh(other_audience_segment)
    db.refresh(other_plan)
    db.close()
    return owner, reviewer, outsider, other_owner, org, brand, product, audience_segment, plan, other_org, other_brand, other_product, other_audience_segment, other_plan


def test_manager_can_create_list_and_get_content_items_with_scope_validation(client):
    owner, reviewer, _, _, org, brand, product, audience_segment, plan, _, _, _, _, _ = seed_content_item_fixture()

    create_response = client.post(
        '/api/v1/content-items',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'product_id': str(product.id),
            'content_plan_id': str(plan.id),
            'audience_segment_id': str(audience_segment.id),
            'scope': 'product',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Drive launch awareness',
            'title': 'Rocket Tea launch reel',
            'status': 'draft',
            'quality_score': 87,
        },
        headers=auth_headers(client, owner.email),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created['organization_id'] == str(org.id)
    assert created['brand_id'] == str(brand.id)
    assert created['product_id'] == str(product.id)
    assert created['content_plan_id'] == str(plan.id)
    assert created['audience_segment_id'] == str(audience_segment.id)
    assert created['scope'] == 'product'
    assert created['quality_score'] == 87

    list_response = client.get(
        f'/api/v1/content-items?organization_id={org.id}&brand_id={brand.id}&scope=product&content_plan_id={plan.id}',
        headers=auth_headers(client, reviewer.email),
    )

    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == created['id']
    assert items[0]['title'] == 'Rocket Tea launch reel'

    get_response = client.get(f"/api/v1/content-items/{created['id']}", headers=auth_headers(client, reviewer.email))

    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched['id'] == created['id']
    assert fetched['content_plan_id'] == str(plan.id)


def test_cannot_create_content_item_without_product_id_for_product_scope(client):
    owner, _, _, _, org, brand, _, _, plan, _, _, _, _, _ = seed_content_item_fixture()

    response = client.post(
        '/api/v1/content-items',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'content_plan_id': str(plan.id),
            'scope': 'product',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Should fail',
            'title': 'Broken item',
            'status': 'draft',
            'quality_score': 12,
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 422
    assert 'product_id is required when scope is product' in response.text


def test_cannot_create_content_item_when_content_plan_does_not_belong_to_brand(client):
    owner, _, _, _, org, brand, product, audience_segment, _, _, _, _, _, other_plan = seed_content_item_fixture()

    response = client.post(
        '/api/v1/content-items',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'product_id': str(product.id),
            'content_plan_id': str(other_plan.id),
            'audience_segment_id': str(audience_segment.id),
            'scope': 'product',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Should fail',
            'title': 'Mismatch item',
            'status': 'draft',
            'quality_score': 12,
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Content plan does not belong to organization and brand'


def test_cannot_create_content_item_when_audience_segment_does_not_belong_to_brand(client):
    owner, _, _, _, org, brand, product, _, plan, _, _, _, other_audience_segment, _ = seed_content_item_fixture()

    response = client.post(
        '/api/v1/content-items',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'product_id': str(product.id),
            'content_plan_id': str(plan.id),
            'audience_segment_id': str(other_audience_segment.id),
            'scope': 'product',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Should fail',
            'title': 'Mismatch segment item',
            'status': 'draft',
            'quality_score': 12,
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Audience segment does not belong to organization and brand'


def test_archived_organization_blocks_content_item_create(client):
    owner, _, _, _, org, brand, _, _, plan, _, _, _, _, _ = seed_content_item_fixture(archived=True)

    response = client.post(
        '/api/v1/content-items',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'content_plan_id': str(plan.id),
            'scope': 'brand',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Should fail',
            'title': 'Frozen item',
            'status': 'draft',
            'quality_score': 12,
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_outsider_cannot_list_content_items_for_inaccessible_organization(client):
    owner, _, outsider, _, org, brand, product, audience_segment, plan, _, _, _, _, _ = seed_content_item_fixture()

    create_response = client.post(
        '/api/v1/content-items',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'product_id': str(product.id),
            'content_plan_id': str(plan.id),
            'audience_segment_id': str(audience_segment.id),
            'scope': 'product',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Should be hidden from outsider',
            'title': 'Visible item',
            'status': 'draft',
            'quality_score': 50,
        },
        headers=auth_headers(client, owner.email),
    )
    assert create_response.status_code == 201

    response = client.get(
        f'/api/v1/content-items?organization_id={org.id}&brand_id={brand.id}',
        headers=auth_headers(client, outsider.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'No access to organization'
