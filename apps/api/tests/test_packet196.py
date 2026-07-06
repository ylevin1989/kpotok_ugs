from app.core.security import hash_password
from app.db.models.audience_segment import AudienceSegment
from app.db.models.brand import Brand
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


def seed_content_plan_generation_fixture(archived: bool = False):
    owner = seed_user('owner-p196@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet196',
        slug='uno-packet196',
        status=OrganizationStatus.ARCHIVED if archived else OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()
    brand = Brand(
        organization_id=org.id,
        name='Rocket Tea 196',
        slug='rocket-tea-p196',
        dna_json={'positioning': 'fast confidence', 'tone': 'direct'},
    )
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-196-001',
        name='Rocket Tea Starter Kit 196',
        category='starter-kit',
        description='Starter kit for plan generation regression.',
        dna_json={'value_props': ['fast setup', 'clear proof']},
    )
    db.add(product)
    db.flush()
    audience_segment = AudienceSegment(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        scope='product',
        name='Busy decision-maker 196',
        description='Needs fast proof and low-friction onboarding.',
        pain_points=['Not enough time'],
        goals=['Move fast'],
        objections=['Too complex'],
        keywords=['quick setup'],
    )
    db.add(audience_segment)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    org_id = str(org.id)
    brand_id = str(brand.id)
    product_id = str(product.id)
    audience_segment_id = str(audience_segment.id)
    db.close()
    return owner, org_id, brand_id, product_id, audience_segment_id


def test_manager_can_generate_content_plans_from_dates_and_dna_context(client):
    owner, org_id, brand_id, product_id, audience_segment_id = seed_content_plan_generation_fixture()

    response = client.post(
        '/api/v1/content-plans/generate',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'product_id': product_id,
            'audience_segment_id': audience_segment_id,
            'scope': 'product',
            'start_date': '2026-07-05',
            'end_date': '2026-07-07',
            'title_prefix': 'Launch week',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Drive launch awareness',
            'status': 'draft',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 201
    items = response.json()['items']
    assert len(items) == 3
    assert [item['date'] for item in items] == ['2026-07-05', '2026-07-06', '2026-07-07']
    assert all(item['scope'] == 'product' for item in items)
    assert all(item['product_id'] == product_id for item in items)
    assert all(item['audience_segment_id'] == audience_segment_id for item in items)
    assert all(item['platform'] == 'instagram' for item in items)
    assert all(item['content_type'] == 'post' for item in items)
    assert all('Launch week —' in item['title'] for item in items)
    assert any('Rocket Tea 196' in item['title'] for item in items)
    assert any('Busy decision-maker 196' in item['title'] for item in items)

    list_response = client.get(
        f'/api/v1/content-plans?organization_id={org_id}&brand_id={brand_id}&scope=product&product_id={product_id}',
        headers=auth_headers(client, owner.email),
    )
    assert list_response.status_code == 200
    assert len(list_response.json()['items']) == 3


def test_generate_content_plans_rejects_product_scope_without_product_id(client):
    owner, org_id, brand_id, _, audience_segment_id = seed_content_plan_generation_fixture()

    response = client.post(
        '/api/v1/content-plans/generate',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'audience_segment_id': audience_segment_id,
            'scope': 'product',
            'start_date': '2026-07-05',
            'end_date': '2026-07-07',
            'title_prefix': 'Launch week',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Drive launch awareness',
            'status': 'draft',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 422
    assert 'product_id is required when scope is product' in response.text
