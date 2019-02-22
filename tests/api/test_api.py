import b2bapi.api
import pytest

def test_can_connect_to_api(api_client, json, logger):
    response = api_client.get('/api/v1/')
    assert json.loads(response.data)['self']=='/api/v1/'

def test_app_raises_404_if_route_unknown(api_client, base_url):
    response = api_client.get('/api/v1/no-route')
    assert response.status_code==404

@pytest.mark.xfail
def test_api_raises_404_if_resource_not_found(api_client):
    response = api_client.get('/api/v1/unknown_resource')
    assert response.status_code==404

def test_api_404_response_is_json(api_client, base_url, json):
    response = api_client.get('/api/v1/unknown_resource')
    assert json.loads(response.data)['code']==404
    # i.e. assert has 'application/json'
    assert len([h for h in response.headers if 'application/json' in h])>=1
