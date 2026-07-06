from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
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


def seed_job_fixture(archived: bool = False):
    owner = seed_user('owner-p22@example.com')
    manager = seed_user('manager-p22@example.com')
    reviewer = seed_user('reviewer-p22@example.com')
    outsider = seed_user('outsider-p22@example.com')
    other_owner = seed_user('other-owner-p22@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet22',
        slug='uno-packet22',
        status=OrganizationStatus.ARCHIVED if archived else OrganizationStatus.ACTIVE,
    )
    other_org = Organization(name='Other Packet22', slug='other-packet22', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.add(other_org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p22')
    other_brand = Brand(organization_id=other_org.id, name='Other Brand', slug='other-brand-p22')
    db.add(brand)
    db.add(other_brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief', content='Need a campaign launch plan.')
    other_brief = Brief(
        organization_id=other_org.id,
        brand_id=other_brand.id,
        title='Other brief',
        content='Belongs to another organization.',
    )
    db.add(brief)
    db.add(other_brief)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.add(OrganizationMembership(organization_id=other_org.id, user_id=other_owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(brief)
    db.refresh(other_org)
    db.refresh(other_brand)
    db.refresh(other_brief)
    db.close()
    return owner, manager, reviewer, outsider, other_owner, org, brand, brief, other_org, other_brand, other_brief


def test_manager_can_create_list_and_get_jobs_for_accessible_brief(client):
    _, manager, reviewer, _, _, org, brand, brief, _, _, _ = seed_job_fixture()

    create_response = client.post(
        '/api/v1/jobs',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'brief_id': str(brief.id),
            'title': 'Generate landing page copy',
        },
        headers=auth_headers(client, manager.email),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created['organization_id'] == str(org.id)
    assert created['brand_id'] == str(brand.id)
    assert created['brief_id'] == str(brief.id)
    assert created['title'] == 'Generate landing page copy'
    assert created['status'] == 'queued'

    list_response = client.get(
        f'/api/v1/jobs?organization_id={org.id}&brand_id={brand.id}&brief_id={brief.id}',
        headers=auth_headers(client, reviewer.email),
    )

    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == created['id']
    assert items[0]['title'] == 'Generate landing page copy'

    get_response = client.get(f"/api/v1/jobs/{created['id']}", headers=auth_headers(client, reviewer.email))

    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched['id'] == created['id']
    assert fetched['brief_id'] == str(brief.id)


def test_cannot_create_job_when_brief_does_not_belong_to_brand_or_organization(client):
    owner, _, _, _, _, org, brand, _, _, _, other_brief = seed_job_fixture()

    response = client.post(
        '/api/v1/jobs',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'brief_id': str(other_brief.id),
            'title': 'Invalid linkage job',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Brief does not belong to organization and brand'


def test_archived_organization_blocks_job_create(client):
    owner, _, _, _, _, org, brand, brief, _, _, _ = seed_job_fixture(archived=True)

    response = client.post(
        '/api/v1/jobs',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'brief_id': str(brief.id),
            'title': 'Frozen job',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_outsider_cannot_list_jobs_for_inaccessible_organization(client):
    owner, _, _, outsider, _, org, brand, brief, _, _, _ = seed_job_fixture()

    create_response = client.post(
        '/api/v1/jobs',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'brief_id': str(brief.id),
            'title': 'Internal execution job',
        },
        headers=auth_headers(client, owner.email),
    )
    assert create_response.status_code == 201

    response = client.get(
        f'/api/v1/jobs?organization_id={org.id}&brand_id={brand.id}&brief_id={brief.id}',
        headers=auth_headers(client, outsider.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'No access to organization'
