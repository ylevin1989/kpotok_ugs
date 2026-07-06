def test_cors_preflight_allows_public_app_origin(client):
    response = client.options(
        '/api/v1/auth/login',
        headers={
            'Origin': 'https://app.uno-ai.pw',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type,authorization',
        },
    )

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'https://app.uno-ai.pw'
    allowed_headers = response.headers['access-control-allow-headers'].lower()
    assert 'content-type' in allowed_headers
    assert 'authorization' in allowed_headers
