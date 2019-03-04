"""
Testing `domains` and catalogs.
"""
import pytest
from b2bapi.db.models.billing import Plan
from b2bapi.db.models.domains import Domain

@pytest.mark.skip('use to dump domains from db')
def test_dump_domains(dump_domains, account_email, nested_session):
    session = nested_session
    dump_domains(session, account_email)


@pytest.mark.skip('use to load domains into db from dump')
def test_load_domains(load_domains, db_connection):
    load_domains(db_connection)


def test_can_check_domain_name_already_exists(
    domain_data, load_domains, nested_session, api_client, jsloads):
    name = domain_data[0]['name']
    # load data dependencies
    load_domains(nested_session.connection())
    query_string = {'q': name}
    response = api_client.get(
        '/api/v1/domain-name-check', query_string=query_string)
    assert response.status_code==200
    

def test_can_check_domain_name_does_not_exist(
    load_signins, nested_session, api_client, jsloads):
    load_signins(nested_session.connection())
    query_string = {'q': 'somedomain'}
    response = api_client.get(
        '/api/v1/domain-name-check', query_string=query_string)
    assert response.status_code==404


def test_can_check_domain_name_is_reserved(
    load_signins, nested_session, api_client, jsloads):
    load_signins(nested_session.connection())
    query_string = {'q': 'admin'}
    response = api_client.get(
        '/api/v1/domain-name-check', query_string=query_string)
    assert response.status_code==403


def test_can_post_domain_with_plan_id(
    load_pricing, load_signins, nested_session, api_client, auth_headers,
    jsloads, account_email):
    conn = nested_session.connection() 
    load_pricing(conn)
    load_signins(conn)
    plan = nested_session.query(Plan).first()
    auth = auth_headers(nested_session, account_email)
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
    jsloads, domain_data, account_email):
    conn = nested_session.connection() 
    load_pricing(conn)
    load_signins(conn)
    plan = nested_session.query(Plan).first()
    auth = auth_headers(nested_session, account_email)
    data = {
        'name': 'lmc',
        'plan_name': plan.name,
        # optional
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


@pytest.mark.skip('Requires validation in API')
def test_rejects_invalid_domain(): pass


def test_can_list_account_domains(
    load_domains, nested_session, api_client, auth_headers,
    jsloads, domain_data, account_email):
    session = nested_session
    load_domains(session.connection())
    auth = auth_headers(session, account_email)
    response = api_client.get('/api/v1/domains', headers=[auth])
    data = jsloads(response.data)
    domains = data['_embedded']['domains']
    assert len(domains)==2
    names = [d['name'] for d in domain_data]
    for domain in domains:
        assert domain['name'] in names
