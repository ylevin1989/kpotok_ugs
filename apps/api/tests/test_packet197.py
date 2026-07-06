from app.core.security import hash_password
from app.db.models.brand import Brand
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


def seed_billing_fixture():
    owner = seed_user('owner-p197@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet197',
        slug='uno-packet197',
        status=OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()
    brand = Brand(
        organization_id=org.id,
        name='Rocket Tea 197',
        slug='rocket-tea-p197',
        dna_json={'positioning': 'fast confidence'},
    )
    db.add(brand)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    org_id = str(org.id)
    brand_id = str(brand.id)
    db.close()
    return owner, org_id, brand_id


def test_manager_can_create_subscription_generate_export_and_track_usage(client):
    owner, org_id, brand_id = seed_billing_fixture()

    subscription_response = client.post(
        '/api/v1/subscriptions',
        json={
            'organization_id': org_id,
            'plan_name': 'starter',
            'monthly_content_plan_limit': 2,
            'monthly_export_limit': 1,
            'is_active': True,
            'current_period_start': '2026-07-01',
            'current_period_end': '2026-07-31',
        },
        headers=auth_headers(client, owner.email),
    )
    assert subscription_response.status_code == 201
    subscription = subscription_response.json()
    assert subscription['plan_name'] == 'starter'
    assert subscription['monthly_content_plan_limit'] == 2
    assert subscription['monthly_export_limit'] == 1

    generated = client.post(
        '/api/v1/content-plans/generate',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'scope': 'brand',
            'start_date': '2026-07-05',
            'end_date': '2026-07-06',
            'title_prefix': 'Billing packet',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Drive awareness',
            'status': 'draft',
        },
        headers=auth_headers(client, owner.email),
    )
    assert generated.status_code == 201
    assert len(generated.json()['items']) == 2

    usage_response = client.get(
        f'/api/v1/subscriptions/usage?organization_id={org_id}',
        headers=auth_headers(client, owner.email),
    )
    assert usage_response.status_code == 200
    usage_items = usage_response.json()['items']
    assert len(usage_items) == 1
    assert usage_items[0]['metric'] == 'content_plan_generation'
    assert usage_items[0]['quantity'] == 2

    export_response = client.post(
        '/api/v1/content-plans/export',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'scope': 'brand',
            'format': 'csv',
        },
        headers=auth_headers(client, owner.email),
    )
    assert export_response.status_code == 200
    assert export_response.headers['content-type'].startswith('text/csv')
    assert 'Billing packet' in export_response.text

    blocked_export = client.post(
        '/api/v1/content-plans/export',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'scope': 'brand',
            'format': 'csv',
        },
        headers=auth_headers(client, owner.email),
    )
    assert blocked_export.status_code == 429
    assert blocked_export.json()['detail'] == 'Monthly export limit exceeded'

    blocked_generation = client.post(
        '/api/v1/content-plans/generate',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'scope': 'brand',
            'start_date': '2026-07-07',
            'end_date': '2026-07-07',
            'title_prefix': 'Over limit',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Should be blocked',
            'status': 'draft',
        },
        headers=auth_headers(client, owner.email),
    )
    assert blocked_generation.status_code == 429
    assert blocked_generation.json()['detail'] == 'Monthly content-plan limit exceeded'

    usage_response = client.get(
        f'/api/v1/subscriptions/usage?organization_id={org_id}',
        headers=auth_headers(client, owner.email),
    )
    assert usage_response.status_code == 200
    usage_items = usage_response.json()['items']
    assert {item['metric'] for item in usage_items} == {'content_plan_generation', 'content_plan_export'}
    generation_record = next(item for item in usage_items if item['metric'] == 'content_plan_generation')
    export_record = next(item for item in usage_items if item['metric'] == 'content_plan_export')
    assert generation_record['quantity'] == 2
    assert export_record['quantity'] == 1
