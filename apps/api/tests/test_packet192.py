from datetime import date

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


def seed_paused_product_dna_fixture():
    owner = seed_user('owner-p192@example.com')
    manager = seed_user('manager-p192@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet192', slug='uno-packet192', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 192', slug='rocket-tea-p192')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-192-001',
        name='Rocket Tea Focus Pack 192',
        category='focus-pack',
        description='Focus pack for paused product-DNA regression.',
    )
    db.add(product)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.commit()
    org_id = str(org.id)
    product_id = str(product.id)
    db.close()
    return owner, manager, org_id, product_id


def test_paused_organization_blocks_product_dna_generation(client):
    owner, manager, org_id, product_id = seed_paused_product_dna_fixture()

    paused = client.patch(
        f'/api/v1/organizations/{org_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    response = client.post(
        f'/api/v1/products/{product_id}/generate-dna',
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Paused organization is read-only for content writes'
