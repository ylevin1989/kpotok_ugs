from datetime import date, datetime, timezone
from uuid import UUID

from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.job import Job
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
from app.db.models.ticket import Ticket
from app.db.models.user import PlatformRole, User
from app.db.session import SessionLocal
from app.domain.billing import get_or_create_subscription, record_usage


def seed_user(
    email: str,
    *,
    password: str = 'test12345',
    platform_role: PlatformRole | None = None,
) -> User:
    db = SessionLocal()
    user = User(
        email=email,
        password_hash=hash_password(password),
        is_active=True,
        platform_role=platform_role,
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


def seed_admin_fixture():
    admin = seed_user('platform-admin-p205@example.com', platform_role=PlatformRole.PLATFORM_ADMIN)
    owner = seed_user('owner-p205@example.com')
    reviewer = seed_user('reviewer-p205@example.com')
    outsider = seed_user('outsider-p205@example.com')

    db = SessionLocal()
    org = Organization(name='Admin Packet205 Org', slug='admin-packet205-org', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()

    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))

    brand = Brand(organization_id=org.id, name='Admin Packet205 Brand', slug='admin-packet205-brand')
    db.add(brand)
    db.flush()

    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='packet205-sku',
        name='Packet205 Product',
        category='saas',
        description='Admin packet 205 fixture',
    )
    db.add(product)
    db.flush()

    plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        scope='product',
        date=date(2026, 7, 7),
        title='Packet205 Plan',
        platform='telegram',
        content_type='post',
        goal='Admin coverage',
        status='approved',
    )
    db.add(plan)
    db.flush()

    brief = Brief(
        organization_id=org.id,
        brand_id=brand.id,
        title='Packet205 Brief',
        content='Admin fixture brief',
    )
    db.add(brief)
    db.flush()

    review_item = ContentItem(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        content_plan_id=plan.id,
        scope='product',
        platform='telegram',
        content_type='post',
        goal='Needs internal review',
        title='Packet205 Internal Review Item',
        status='internal_review',
        quality_score=72,
    )
    db.add(review_item)
    db.flush()

    ticket = Ticket(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        content_item_id=review_item.id,
        type='content_revision',
        reason_codes=['tone_mismatch'],
        comment='Needs adjustments',
        status='open',
        priority='high',
        assigned_agent_role='editor',
        created_by_id=owner.id,
    )
    db.add(ticket)
    db.flush()

    failed_job = Job(
        organization_id=org.id,
        brand_id=brand.id,
        brief_id=brief.id,
        title='Packet205 Failed Job',
        status='failed',
        kind='manual',
        error_message='worker failed',
        finished_at=datetime.now(timezone.utc),
    )
    queued_job = Job(
        organization_id=org.id,
        brand_id=brand.id,
        brief_id=brief.id,
        title='Packet205 Queued Job',
        status='queued',
        kind='manual',
    )
    db.add_all([failed_job, queued_job])
    db.commit()

    payload = {
        'admin': admin,
        'owner': owner,
        'reviewer': reviewer,
        'outsider': outsider,
        'organization_id': str(org.id),
        'brand_id': str(brand.id),
        'brief_id': str(brief.id),
        'failed_job_id': str(failed_job.id),
        'queued_job_id': str(queued_job.id),
        'ticket_id': str(ticket.id),
        'content_item_id': str(review_item.id),
    }
    db.close()
    return payload


def test_platform_admin_can_list_admin_surfaces_and_audit_sensitive_actions(client):
    fixture = seed_admin_fixture()
    owner_headers = auth_headers(client, fixture['owner'].email)
    admin_headers = auth_headers(client, fixture['admin'].email)

    add_member_response = client.post(
        f"/api/v1/organizations/{fixture['organization_id']}/members",
        json={'email': fixture['reviewer'].email, 'role': 'client_reviewer'},
        headers=owner_headers,
    )
    assert add_member_response.status_code == 201
    membership_id = add_member_response.json()['id']

    role_response = client.patch(
        f"/api/v1/organizations/{fixture['organization_id']}/members/{membership_id}",
        json={'role': 'client_manager'},
        headers=owner_headers,
    )
    assert role_response.status_code == 200

    subscription_response = client.post(
        '/api/v1/subscriptions',
        json={
            'organization_id': fixture['organization_id'],
            'plan_name': 'growth',
            'monthly_content_plan_limit': 50,
            'monthly_export_limit': 25,
            'is_active': True,
            'current_period_start': '2026-07-01',
            'current_period_end': '2026-07-31',
        },
        headers=owner_headers,
    )
    assert subscription_response.status_code == 201

    status_response = client.patch(
        f"/api/v1/organizations/{fixture['organization_id']}",
        json={'status': 'paused'},
        headers=owner_headers,
    )
    assert status_response.status_code == 200

    db = SessionLocal()
    subscription = get_or_create_subscription(db, UUID(subscription_response.json()['organization_id']))
    record_usage(
        db,
        organization_id=subscription.organization_id,
        subscription=subscription,
        metric='content_plan_export',
        quantity=3,
        metadata={'source': 'packet205'},
    )
    db.close()

    clients_response = client.get('/api/v1/admin/clients', headers=admin_headers)
    assert clients_response.status_code == 200
    assert clients_response.json()['items'][0]['slug'] == 'admin-packet205-org'

    tickets_response = client.get('/api/v1/admin/tickets', headers=admin_headers)
    assert tickets_response.status_code == 200
    assert tickets_response.json()['items'][0]['id'] == fixture['ticket_id']

    review_response = client.get('/api/v1/admin/content-review', headers=admin_headers)
    assert review_response.status_code == 200
    assert review_response.json()['items'][0]['id'] == fixture['content_item_id']
    assert review_response.json()['items'][0]['status'] == 'internal_review'

    usage_response = client.get('/api/v1/admin/usage', headers=admin_headers)
    assert usage_response.status_code == 200
    assert usage_response.json()['items'][0]['metric'] == 'content_plan_export'

    cancel_response = client.post(f"/api/v1/admin/jobs/{fixture['queued_job_id']}/cancel", headers=admin_headers)
    assert cancel_response.status_code == 200
    assert cancel_response.json()['status'] == 'cancelled'

    retry_response = client.post(f"/api/v1/admin/jobs/{fixture['failed_job_id']}/retry", headers=admin_headers)
    assert retry_response.status_code == 200
    assert retry_response.json()['status'] == 'queued'

    jobs_response = client.get('/api/v1/admin/jobs', headers=admin_headers)
    assert jobs_response.status_code == 200
    jobs_by_id = {item['id']: item for item in jobs_response.json()['items']}
    assert jobs_by_id[fixture['queued_job_id']]['status'] == 'cancelled'
    assert jobs_by_id[fixture['failed_job_id']]['status'] == 'queued'

    audit_response = client.get('/api/v1/admin/audit-logs', headers=admin_headers)
    assert audit_response.status_code == 200
    actions = {item['action'] for item in audit_response.json()['items']}
    assert 'organization_member_role_changed' in actions
    assert 'organization_status_changed' in actions
    assert 'subscription_upserted' in actions
    assert 'admin_job_cancelled' in actions
    assert 'admin_job_retried' in actions

    retry_audit = next(item for item in audit_response.json()['items'] if item['action'] == 'admin_job_retried')
    assert retry_audit['entity_type'] == 'job'
    assert retry_audit['entity_id'] == fixture['failed_job_id']
    assert retry_audit['organization_id'] == fixture['organization_id']
    assert retry_audit['metadata_json']['from_status'] == 'failed'
    assert retry_audit['metadata_json']['to_status'] == 'queued'


def test_client_roles_cannot_access_admin_routes(client):
    fixture = seed_admin_fixture()
    owner_headers = auth_headers(client, fixture['owner'].email)

    clients_response = client.get('/api/v1/admin/clients', headers=owner_headers)
    assert clients_response.status_code == 403
    assert clients_response.json()['detail'] == 'Platform admin access required'

    cancel_response = client.post(f"/api/v1/admin/jobs/{fixture['queued_job_id']}/cancel", headers=owner_headers)
    assert cancel_response.status_code == 403
    assert cancel_response.json()['detail'] == 'Platform admin access required'
