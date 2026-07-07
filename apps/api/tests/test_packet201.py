from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
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


def seed_active_brand_fixture():
    owner = seed_user('owner-p201@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet201', slug='uno-packet201', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Pause-safe Brand', slug='pause-safe-brand')
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Brand lifecycle brief', content='Lifecycle coverage seed.')
    db.add(brief)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.close()
    return owner, str(org.id), str(brand.id)


def test_paused_brand_blocks_product_creation(client):
    owner, org_id, brand_id = seed_active_brand_fixture()

    paused = client.patch(
        f'/api/v1/brands/{brand_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    response = client.post(
        '/api/v1/products',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'sku': 'paused-brand-product',
            'name': 'Paused Brand Product',
            'category': 'lifecycle',
            'description': 'Paused brands should not accept new product writes.',
        },
        headers=auth_headers(client, owner.email),
    )
    assert response.status_code == 409
    assert response.json()['detail'] == 'Paused brand is read-only for content writes'


def test_archived_brand_blocks_brand_update_and_dna_generation(client):
    owner, org_id, brand_id = seed_active_brand_fixture()

    archived = client.patch(
        f'/api/v1/brands/{brand_id}',
        json={'status': 'archived'},
        headers=auth_headers(client, owner.email),
    )
    assert archived.status_code == 200
    assert archived.json()['status'] == 'archived'

    update_response = client.patch(
        f'/api/v1/brands/{brand_id}',
        json={'name': 'Archived rename attempt'},
        headers=auth_headers(client, owner.email),
    )
    assert update_response.status_code == 409
    assert update_response.json()['detail'] == 'Archived brand is read-only'

    dna_response = client.post(
        f'/api/v1/brands/{brand_id}/generate-dna',
        headers=auth_headers(client, owner.email),
    )
    assert dna_response.status_code == 409
    assert dna_response.json()['detail'] == 'Archived brand is read-only for content writes'
