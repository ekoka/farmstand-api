"""
Testing `domains` and catalogs.
"""
import pytest
from b2bapi.db.models.billing import Plan
from b2bapi.db.models.domains import Domain


def test_can_check_domain_name_does_not_exist(
    load_signins, nested_session, api_client, auth_headers, jsloads):
    load_signins(nested_session.connection())
    auth = auth_headers(nested_session, 'verysimple@gmail.com')
    query_string = {'q': 'somedomain'}
    response = api_client.get('/api/v1/domain-name-check', headers=[auth])
    assert response.status_code==404


def test_can_post_domain_with_plan_id(
    load_pricing, load_signins, nested_session, api_client, auth_headers,
    jsloads):
    conn = nested_session.connection() 
    load_pricing(conn)
    load_signins(conn)
    plan = nested_session.query(Plan).first()
    auth = auth_headers(nested_session, 'verysimple@gmail.com')
    data = {
        'name': 'Lao Mountain Coffee',
        'plan_id': plan.plan_id,
        'details': {
            'label': {
                'en': 'Lao Mountain Coffee',
                'fr': 'Le Café des Montagnes du Laos',
            },
        }
    }
    response = api_client.post(
        '/api/v1/domains',
        headers=[auth],
        json=data,
    )
    assert response.status_code==201

def test_can_post_domain_with_plan_name(
    load_pricing, load_signins, nested_session, api_client, auth_headers,
    jsloads):
    conn = nested_session.connection() 
    load_pricing(conn)
    load_signins(conn)
    plan = nested_session.query(Plan).first()
    auth = auth_headers(nested_session, 'verysimple@gmail.com')
    data = {
        'name': 'Lao Mountain Coffee',
        'plan_name': plan.name,
        'details': {
            'label': {
                'en': 'Lao Mountain Coffee',
                'fr': 'Le Café des Montagnes du Laos',
            },
        }
    }
    response = api_client.post(
        '/api/v1/domains',
        headers=[auth],
        json=data,
    )
    assert response.status_code==201

@pytest.mark.skip
def test_can_check_domain_name_exists(access_key_finder, nested_session):
    pass
#def test_can_create_domain(access_key_finder, nested_session):
#    findkey = access_key_finder(nested_session)
