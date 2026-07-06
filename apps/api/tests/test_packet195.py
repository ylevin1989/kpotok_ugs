from app.core.security import hash_password
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


def seed_product_fixture(archived: bool = False):
    owner = seed_user('owner-p195@example.com')
    reviewer = seed_user('reviewer-p195@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet195',
        slug='uno-packet195',
        status=OrganizationStatus.ARCHIVED if archived else OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 195', slug='rocket-tea-p195')
    db.add(brand)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    org_id = str(org.id)
    brand_id = str(brand.id)
    db.close()
    return owner, reviewer, org_id, brand_id


def create_product(client, owner_email: str, org_id: str, brand_id: str, sku: str, name: str):
    response = client.post(
        '/api/v1/products',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'sku': sku,
            'name': name,
            'category': 'starter-kit',
            'description': f'{name} description',
            'features': ['Fast setup'],
            'benefits': ['Easy onboarding'],
            'proofs': ['Pilot result'],
            'objections': ['Too complex'],
            'restrictions': ['Not for wholesale'],
            'status': 'draft',
            'readiness_score': 25,
        },
        headers=auth_headers(client, owner_email),
    )
    assert response.status_code == 201
    return response.json()


def test_manager_can_update_product_and_retrieve_changes(client):
    owner, reviewer, org_id, brand_id = seed_product_fixture()
    created = create_product(client, owner.email, org_id, brand_id, 'SKU-195-001', 'Rocket Tea Starter Kit')

    response = client.patch(
        f"/api/v1/products/{created['id']}",
        json={
            'name': 'Rocket Tea Pro Kit',
            'category': 'pro-kit',
            'description': 'An updated description for the pro kit.',
            'features': ['Fast setup', 'Portable'],
            'benefits': ['Easy onboarding', 'Higher retention'],
            'proofs': ['Updated pilot result'],
            'objections': ['Price'],
            'restrictions': ['No resale'],
            'status': 'ready',
            'readiness_score': 88,
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated['id'] == created['id']
    assert updated['sku'] == 'SKU-195-001'
    assert updated['name'] == 'Rocket Tea Pro Kit'
    assert updated['category'] == 'pro-kit'
    assert updated['features'] == ['Fast setup', 'Portable']
    assert updated['status'] == 'ready'
    assert updated['readiness_score'] == 88

    fetched = client.get(f"/api/v1/products/{created['id']}", headers=auth_headers(client, reviewer.email))
    assert fetched.status_code == 200
    body = fetched.json()
    assert body['name'] == 'Rocket Tea Pro Kit'
    assert body['status'] == 'ready'
    assert body['readiness_score'] == 88


def test_archived_organization_blocks_product_update(client):
    owner, _, org_id, brand_id = seed_product_fixture()
    created = create_product(client, owner.email, org_id, brand_id, 'SKU-195-002', 'Archived candidate')

    archived = client.patch(
        f'/api/v1/organizations/{org_id}',
        json={'status': 'archived'},
        headers=auth_headers(client, owner.email),
    )
    assert archived.status_code == 200
    assert archived.json()['status'] == 'archived'

    response = client.patch(
        f"/api/v1/products/{created['id']}",
        json={'name': 'Should not update'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_manager_cannot_update_product_to_duplicate_sku_in_brand(client):
    owner, _, org_id, brand_id = seed_product_fixture()
    product_one = create_product(client, owner.email, org_id, brand_id, 'SKU-195-010', 'First product')
    product_two = create_product(client, owner.email, org_id, brand_id, 'SKU-195-011', 'Second product')

    response = client.patch(
        f"/api/v1/products/{product_two['id']}",
        json={'sku': product_one['sku']},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Product SKU already exists in organization and brand'
