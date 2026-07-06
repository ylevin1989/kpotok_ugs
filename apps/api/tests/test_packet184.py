from pathlib import Path

from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.organization_permission_event import OrganizationPermissionEvent
from app.db.models.user import User
from app.db.session import SessionLocal


REPO_ROOT = Path(__file__).resolve().parents[3]


def seed_user(email: str, password: str = 'test12345', full_name: str | None = None) -> User:
    from app.core.security import hash_password

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


def seed_audit_scope(seed_slug: str):
    owner = seed_user(f'{seed_slug}-owner@example.com')
    target = seed_user(f'{seed_slug}-target@example.com')
    db = SessionLocal()
    org = Organization(name=f'{seed_slug} Org', slug=f'{seed_slug}-org', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    org_id = org.id
    db.add(OrganizationMembership(organization_id=org_id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.close()
    return owner, target, org_id


def test_permission_changes_are_persisted_and_listable(client):
    owner, target, org_id = seed_audit_scope('packet184')

    create_response = client.post(
        f'/api/v1/organizations/{org_id}/members',
        json={'email': target.email, 'role': 'client_reviewer'},
        headers=auth_headers(client, owner.email),
    )
    assert create_response.status_code == 201

    db = SessionLocal()
    created_membership = db.query(OrganizationMembership).filter_by(organization_id=org_id, user_id=target.id).one()
    created_membership_id = created_membership.id
    db.close()

    update_response = client.patch(
        f'/api/v1/organizations/{org_id}/members/{created_membership_id}',
        json={'role': 'client_manager'},
        headers=auth_headers(client, owner.email),
    )
    assert update_response.status_code == 200

    delete_response = client.delete(
        f'/api/v1/organizations/{org_id}/members/{created_membership_id}',
        headers=auth_headers(client, owner.email),
    )
    assert delete_response.status_code == 204

    status_response = client.patch(
        f'/api/v1/organizations/{org_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert status_response.status_code == 200

    db = SessionLocal()
    events = db.query(OrganizationPermissionEvent).filter_by(organization_id=org_id).all()
    assert {event.action for event in events} == {
        'membership_created',
        'membership_role_changed',
        'membership_deleted',
        'organization_status_changed',
    }
    created_event = next(event for event in events if event.action == 'membership_created')
    assert created_event.actor_user_id == owner.id
    assert created_event.target_type == 'membership'
    assert created_event.details_json is not None and 'client_reviewer' in created_event.details_json
    db.close()

    list_response = client.get(
        f'/api/v1/organizations/{org_id}/permission-events',
        headers=auth_headers(client, owner.email),
    )
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload['items']) == 4
    assert {item['action'] for item in payload['items']} == {
        'membership_created',
        'membership_role_changed',
        'membership_deleted',
        'organization_status_changed',
    }
    assert payload['items'][0]['action'] == 'organization_status_changed'
    assert payload['items'][0]['details']['from'] == 'active'
    assert payload['items'][0]['details']['to'] == 'paused'


def test_audit_log_documentation_covers_permission_events():
    doc_path = REPO_ROOT / 'docs/organization-permission-audit-log.md'
    policy_path = REPO_ROOT / 'docs/organization-membership-role-policy.md'
    roadmap_path = REPO_ROOT / 'ROADMAP.md'

    doc_text = doc_path.read_text()
    policy_text = policy_path.read_text()
    roadmap_text = roadmap_path.read_text()

    assert '# Organization permission audit log' in doc_text
    assert 'membership_created' in doc_text
    assert 'permission-events' in doc_text
    assert 'Sensitive permission changes are audit logged' in policy_text
    assert 'Packet 07' in roadmap_text
