from datetime import date

from app.core.security import hash_password
from app.db.enums import GenerationType
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.content_version import ContentVersion
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
from app.db.models.ticket import Ticket
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


def seed_quality_check_fixture():
    owner = seed_user('owner-p174@example.com')
    reviewer = seed_user('reviewer-p174@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet174', slug='uno-packet174', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 174', slug='rocket-tea-p174')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-174-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for paused quality-check regression.',
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
        title='Rocket Tea QA week 174',
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
        title='QA post 174',
        content_type='post',
        platform='instagram',
        goal='Drive launch awareness',
        status='draft',
        quality_score=42,
    )
    db.add(content_item)
    db.flush()
    version = ContentVersion(
        organization_id=org.id,
        content_item_id=content_item.id,
        version_number=1,
        body_markdown='# QA post 174\n\nDraft body.',
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
    ticket = Ticket(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        content_item_id=content_item.id,
        content_version_id=version.id,
        type='revision_request',
        reason_codes=['needs_clarity'],
        comment='Needs sharper CTA.',
        status='open',
        priority='normal',
        assigned_agent_role='content_creator',
        created_by_id=reviewer.id,
        resolved_at=None,
    )
    db.add(ticket)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(product)
    db.refresh(content_plan)
    db.refresh(content_item)
    db.refresh(version)
    db.refresh(ticket)
    org_id = str(org.id)
    content_item_id = str(content_item.id)
    ticket_id = str(ticket.id)
    db.close()
    return owner, org_id, content_item_id, ticket_id


def test_paused_organization_blocks_quality_check_create(client):
    owner, org_id, content_item_id, ticket_id = seed_quality_check_fixture()

    paused = client.patch(
        f'/api/v1/organizations/{org_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    response = client.post(
        f'/api/v1/content-items/{content_item_id}/quality-check',
        json={
            'organization_id': org_id,
            'ticket_id': ticket_id,
            'score': 91,
            'threshold': 80,
            'status': 'passed',
            'summary': 'Content is on-brand and readable.',
            'checks_json': {'brand_voice': True, 'readability': 93},
            'issues_json': [],
            'recommendations_json': ['Publish as-is.'],
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Paused organization is read-only for content writes'
