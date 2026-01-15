def test_health(mocked_client):
    response = mocked_client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
