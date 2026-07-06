from datetime import date

from app.core.security import hash_password
from app.db.enums import GenerationType
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.content_version import ContentVersion
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
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


def seed_review_fixture(archived: bool = False):
    owner = seed_user('owner-p167@example.com')
    reviewer = seed_user('reviewer-p167@example.com')
    outsider = seed_user('outsider-p167@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet167',
        slug='uno-packet167',
        status=OrganizationStatus.ARCHIVED if archived else OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p167')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-167-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for tickets.',
    )
    db.add(product)
    db.flush()
    content_plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        audience_segment_id=None,
        scope='product',
        date=date(2026, 7, 5),
        title='Rocket Tea review week',
        platform='instagram',
        content_type='post',
        goal='Drive launch awareness',
        status='draft',
    )
    db.add(content_plan)
    db.flush()
    content_item = ContentItem(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        content_plan_id=content_plan.id,
        current_version_id=None,
        title='Review post',
        content_type='post',
        platform='instagram',
        goal='Drive launch awareness',
        status='draft',
    )
    db.add(content_item)
    db.flush()
    version = ContentVersion(
        organization_id=org.id,
        content_item_id=content_item.id,
        version_number=1,
        body_markdown='# Review post\n\nDraft body.',
        structured_json={'headline': 'Draft body'},
        change_summary='Initial draft',
        generation_type=GenerationType.INITIAL,
        generated_from_task_id=None,
        created_by=owner.id,
        is_current=True,
    )
    db.add(version)
    db.flush()
    content_item.current_version_id = version.id
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(product)
    db.refresh(content_plan)
    db.refresh(content_item)
    db.refresh(version)
    db.close()
    return owner, reviewer, outsider, org, brand, product, content_plan, content_item, version


def test_manager_can_reject_content_item_and_ticket_is_listable(client):
    owner, reviewer, _, org, _, _, _, content_item, version = seed_review_fixture()

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/reject',
        json={
            'reason_codes': ['off_brand', 'needs_clarification'],
            'comment': 'Needs a tighter angle.',
            'priority': 'high',
            'assigned_agent_role': 'content_creator',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 201
    ticket = response.json()
    assert ticket['organization_id'] == str(org.id)
    assert ticket['content_item_id'] == str(content_item.id)
    assert ticket['content_version_id'] == str(version.id)
    assert ticket['type'] == 'rejection'
    assert ticket['status'] == 'open'
    assert ticket['priority'] == 'high'
    assert ticket['reason_codes'] == ['off_brand', 'needs_clarification']

    item_response = client.get(f'/api/v1/content-items/{content_item.id}', headers=auth_headers(client, reviewer.email))
    assert item_response.status_code == 200
    assert item_response.json()['status'] == 'rejected'
    assert item_response.json()['current_version_id'] == str(version.id)

    list_response = client.get(
        f'/api/v1/tickets?organization_id={org.id}&content_item_id={content_item.id}',
        headers=auth_headers(client, reviewer.email),
    )
    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == ticket['id']

    get_response = client.get(f"/api/v1/tickets/{ticket['id']}", headers=auth_headers(client, reviewer.email))
    assert get_response.status_code == 200
    assert get_response.json()['id'] == ticket['id']


def test_manager_can_request_revision(client):
    owner, _, _, _, _, _, _, content_item, version = seed_review_fixture()

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/request-revision',
        json={
            'reason_codes': ['missing_proof'],
            'comment': 'Add an example with measurable outcome.',
            'priority': 'normal',
            'assigned_agent_role': 'content_creator',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 201
    ticket = response.json()
    assert ticket['type'] == 'revision_request'
    assert ticket['status'] == 'open'
    assert ticket['content_version_id'] == str(version.id)

    item_response = client.get(f'/api/v1/content-items/{content_item.id}', headers=auth_headers(client, owner.email))
    assert item_response.status_code == 200
    assert item_response.json()['status'] == 'revision_requested'


def test_manager_can_approve_content_item(client):
    owner, _, _, _, _, _, _, content_item, version = seed_review_fixture()

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/approve',
        json={'comment': 'Looks good.', 'priority': 'normal', 'assigned_agent_role': 'reviewer'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 201
    ticket = response.json()
    assert ticket['type'] == 'approval'
    assert ticket['status'] == 'resolved'
    assert ticket['content_version_id'] == str(version.id)
    assert ticket['resolved_at'] is not None

    item_response = client.get(f'/api/v1/content-items/{content_item.id}', headers=auth_headers(client, owner.email))
    assert item_response.status_code == 200
    assert item_response.json()['status'] == 'approved'


def test_outsider_cannot_create_review_ticket(client):
    _, _, outsider, _, _, _, _, content_item, _ = seed_review_fixture()

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/reject',
        json={'reason_codes': ['off_brand']},
        headers=auth_headers(client, outsider.email),
    )

    assert response.status_code == 403


def test_archived_organization_blocks_review_actions(client):
    owner, _, _, org, _, _, _, content_item, _ = seed_review_fixture(archived=True)

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/approve',
        json={'comment': 'Looks fine.'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'
