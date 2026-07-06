from app.core.config import settings
from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
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


def seed_paused_org_fixture(title: str):
    owner = seed_user(f"{title.replace(' ', '-').lower()}@example.com")
    db = SessionLocal()
    org = Organization(name='Uno Packet171', slug=f"uno-packet171-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 171', slug=f"rocket-tea-p171-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 171', content='Need a campaign launch plan 171.')
    db.add(brief)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(brief)
    org_id = str(org.id)
    brand_id = str(brand.id)
    db.close()
    return owner, org_id, brand_id


def test_paused_organization_blocks_brief_creation(client):
    owner, org_id, brand_id = seed_paused_org_fixture('Packet 171 paused brief creation')

    paused = client.patch(
        f'/api/v1/organizations/{org_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    response = client.post(
        '/api/v1/briefs',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'title': 'Paused brief should fail',
            'content': 'Paused orgs should not accept new briefs.',
        },
        headers=auth_headers(client, owner.email),
    )
    assert response.status_code == 409
    assert response.json()['detail'] == 'Paused organization is read-only for content writes'


def test_paused_organization_blocks_brand_update(client):
    owner, org_id, brand_id = seed_paused_org_fixture('Packet 171 paused brand update')

    paused = client.patch(
        f'/api/v1/organizations/{org_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    response = client.patch(
        f'/api/v1/brands/{brand_id}',
        json={'name': 'Paused brand should fail'},
        headers=auth_headers(client, owner.email),
    )
    assert response.status_code == 409
    assert response.json()['detail'] == 'Paused organization is read-only for content writes'
