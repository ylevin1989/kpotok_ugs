from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
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


def seed_brief_fixture(archived: bool = False):
    owner = seed_user('owner-p21@example.com')
    reviewer = seed_user('reviewer-p21@example.com')
    outsider = seed_user('outsider-p21@example.com')
    other_owner = seed_user('other-owner-p21@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet21',
        slug='uno-packet21',
        status=OrganizationStatus.ARCHIVED if archived else OrganizationStatus.ACTIVE,
    )
    other_org = Organization(name='Other Packet21', slug='other-packet21', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.add(other_org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea')
    other_brand = Brand(organization_id=other_org.id, name='Other Brand', slug='other-brand')
    db.add(brand)
    db.add(other_brand)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.add(OrganizationMembership(organization_id=other_org.id, user_id=other_owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(other_org)
    db.refresh(other_brand)
    db.close()
    return owner, reviewer, outsider, other_owner, org, brand, other_org, other_brand


def test_manager_can_create_list_and_get_briefs_within_accessible_brand(client):
    owner, reviewer, _, _, org, brand, _, _ = seed_brief_fixture()

    create_response = client.post(
        '/api/v1/briefs',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'title': 'Launch spring collection',
            'content': 'Need a launch brief with audience, offers, and channels.',
        },
        headers=auth_headers(client, owner.email),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created['organization_id'] == str(org.id)
    assert created['brand_id'] == str(brand.id)
    assert created['title'] == 'Launch spring collection'
    assert created['content'] == 'Need a launch brief with audience, offers, and channels.'

    list_response = client.get(
        f'/api/v1/briefs?organization_id={org.id}&brand_id={brand.id}',
        headers=auth_headers(client, reviewer.email),
    )

    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == created['id']
    assert items[0]['title'] == 'Launch spring collection'

    get_response = client.get(f"/api/v1/briefs/{created['id']}", headers=auth_headers(client, reviewer.email))

    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched['id'] == created['id']
    assert fetched['brand_id'] == str(brand.id)


def test_cannot_create_brief_when_brand_does_not_belong_to_organization(client):
    owner, _, _, _, org, _, _, other_brand = seed_brief_fixture()

    response = client.post(
        '/api/v1/briefs',
        json={
            'organization_id': str(org.id),
            'brand_id': str(other_brand.id),
            'title': 'Mismatch brief',
            'content': 'This should fail because the brand belongs elsewhere.',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Brand does not belong to organization'


def test_archived_organization_blocks_brief_create(client):
    owner, _, _, _, org, brand, _, _ = seed_brief_fixture(archived=True)

    response = client.post(
        '/api/v1/briefs',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'title': 'Frozen brief',
            'content': 'Should not be writable while org is archived.',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_outsider_cannot_list_briefs_for_inaccessible_organization(client):
    owner, _, outsider, _, org, brand, _, _ = seed_brief_fixture()

    create_response = client.post(
        '/api/v1/briefs',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'title': 'Visible only inside org',
            'content': 'Outsider should not see this.',
        },
        headers=auth_headers(client, owner.email),
    )
    assert create_response.status_code == 201

    response = client.get(
        f'/api/v1/briefs?organization_id={org.id}&brand_id={brand.id}',
        headers=auth_headers(client, outsider.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'No access to organization'
