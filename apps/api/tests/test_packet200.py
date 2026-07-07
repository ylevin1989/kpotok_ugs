from app.core.security import hash_password
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import PlatformRole, User
from app.db.session import SessionLocal


def seed_user(
    email: str,
    password: str = 'test12345',
    full_name: str | None = None,
    platform_role: PlatformRole | None = None,
) -> User:
    db = SessionLocal()
    user = User(
        email=email,
        full_name=full_name or email.split('@')[0].title(),
        password_hash=hash_password(password),
        platform_role=platform_role,
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


def seed_org(owner: User, name: str, slug: str) -> Organization:
    db = SessionLocal()
    org = Organization(name=name, slug=slug, status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.close()
    return org


def test_platform_admin_can_lookup_user_by_email_and_memberships(client):
    admin = seed_user('platform-admin-p200@example.com', platform_role=PlatformRole.PLATFORM_ADMIN)
    subject = seed_user('subject-p200@example.com', full_name='Support Subject')
    org = seed_org(admin, 'Support Org', 'support-org-p200')

    db = SessionLocal()
    db.add(OrganizationMembership(organization_id=org.id, user_id=subject.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.close()

    response = client.get(
        '/api/v1/support/users',
        params={'email': subject.email},
        headers=auth_headers(client, admin.email),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['user']['email'] == subject.email
    assert payload['user']['platform_role'] is None
    assert payload['memberships'][0]['organization_name'] == 'Support Org'
    assert payload['memberships'][0]['organization_slug'] == 'support-org-p200'
    assert payload['memberships'][0]['role'] == 'client_reviewer'


def test_non_admin_cannot_use_support_lookup(client):
    user = seed_user('regular-p200@example.com')
    target = seed_user('target-p200@example.com')

    response = client.get(
        '/api/v1/support/users',
        params={'email': target.email},
        headers=auth_headers(client, user.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Platform admin access required'
