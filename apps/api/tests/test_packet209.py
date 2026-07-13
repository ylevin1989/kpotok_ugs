from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal


def seed_user(email: str, password: str = 'test12345') -> User:
    db = SessionLocal()
    user = User(email=email, full_name=email.split('@')[0].title(), password_hash=hash_password(password), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers(client, email: str, password: str = 'test12345') -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def seed_org_with_manager():
    owner = seed_user('owner-p209@example.com')
    db = SessionLocal()
    org = Organization(name='Uno P209', slug='uno-p209', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_MANAGER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner, str(org.id)


def test_brand_create_update_and_dna_request_include_brand_fields(client):
    owner, org_id = seed_org_with_manager()
    headers = auth_headers(client, owner.email)

    create_response = client.post(
        '/api/v1/brands',
        json={
            'organization_id': org_id,
            'name': 'Starter Brand',
            'slug': 'starter-brand',
            'positioning': 'clear practical setup',
            'tone_of_voice': ['clear', 'direct'],
            'mission': 'Help teams launch faster',
            'values': ['clarity', 'speed'],
            'forbidden_claims': ['Guaranteed results'],
            'allowed_claims': ['Fast setup'],
            'competitors': ['Competitor A'],
            'good_examples': ['Short helpful copy'],
            'bad_examples': ['Overpromising hype'],
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created['positioning'] == 'clear practical setup'
    assert created['tone_of_voice'] == ['clear', 'direct']
    assert created['forbidden_claims'] == ['Guaranteed results']
    assert created['bad_examples'] == ['Overpromising hype']

    brand_id = created['id']
    update_response = client.patch(
        f'/api/v1/brands/{brand_id}',
        json={
            'mission': 'Help teams launch with confidence',
            'allowed_claims': ['Fast setup', 'Simple workflows'],
            'competitors': ['Competitor A', 'Competitor B'],
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated['mission'] == 'Help teams launch with confidence'
    assert updated['allowed_claims'] == ['Fast setup', 'Simple workflows']
    assert updated['competitors'] == ['Competitor A', 'Competitor B']

    dna_response = client.post(f'/api/v1/brands/{brand_id}/generate-dna', headers=headers)
    assert dna_response.status_code == 201
    job = dna_response.json()
    request = job['brief_content']
    assert request is not None
    assert '"positioning": "clear practical setup"' in request
    assert '"forbidden_claims": ["Guaranteed results"]' in request
    assert '"good_examples": ["Short helpful copy"]' in request
