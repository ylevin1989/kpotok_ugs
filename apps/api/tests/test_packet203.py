def test_register_to_brand_creation_smoke_and_paused_guard(client):
    register = client.post(
        '/api/v1/auth/register',
        json={
            'email': 'packet203@example.com',
            'full_name': 'Packet 203',
            'password': 'test12345',
        },
    )
    assert register.status_code == 201
    token = register.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    org_response = client.post('/api/v1/organizations', json={'name': 'Packet 203 Org', 'slug': 'packet-203-org'}, headers=headers)
    assert org_response.status_code == 201
    org = org_response.json()
    assert org['status'] == 'active'

    brand_response = client.post(
        '/api/v1/brands',
        json={
            'organization_id': org['id'],
            'name': 'Packet 203 Brand',
            'slug': 'packet-203-brand',
        },
        headers=headers,
    )
    assert brand_response.status_code == 201
    brand = brand_response.json()
    assert brand['status'] == 'active'
    assert brand['organization_id'] == org['id']

    product_response = client.post(
        '/api/v1/products',
        json={
            'organization_id': org['id'],
            'brand_id': brand['id'],
            'sku': 'packet-203-product',
            'name': 'Packet 203 Product',
            'category': 'integration',
            'description': 'Critical-path lane smoke coverage for postgres-backed API tests.',
        },
        headers=headers,
    )
    assert product_response.status_code == 201
    product = product_response.json()
    assert product['brand_id'] == brand['id']

    paused = client.patch(
        f"/api/v1/brands/{brand['id']}",
        json={'status': 'paused'},
        headers=headers,
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    blocked = client.post(
        '/api/v1/products',
        json={
            'organization_id': org['id'],
            'brand_id': brand['id'],
            'sku': 'packet-203-blocked',
            'name': 'Packet 203 Blocked Product',
            'category': 'integration',
            'description': 'Paused brands must reject new content writes.',
        },
        headers=headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()['detail'] == 'Paused brand is read-only for content writes'
