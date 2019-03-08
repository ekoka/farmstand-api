import pytest
import json
from urllib import parse
import stripe

from b2bapi.db.models.accounts import Account, AccountAccessKey, Signin
from ..conftest import cannot_reach_stripe

@pytest.mark.skipif(cannot_reach_stripe(), reason='Could not reach stripe')
def test_can_create_account_with_simpleb2b(
    api_client, account_data, nested_session):
    # simpleb2b as provider
    # TODO change this to `productlist`
    response = api_client.post('/api/v1/accounts', json=account_data[0])
    acc = nested_session.execute('select * from accounts').fetchone()
    customer = stripe.Customer.retrieve(acc.stripe_customer_id)

    assert acc.email==account_data[0]['token']['email']
    assert acc.lang==account_data[0]['token']['lang']
    assert customer['id']==acc.stripe_customer_id
    customer.delete()


@pytest.mark.skip('Use to populated and dump db with account data.')
def test_dump_accounts(dump_accounts, nested_session):
    connection = nested_session.connection()
    dump_accounts(connection)

def test_can_create_signin(load_accounts, nested_session, api_client, logger):
    # preload db with accounts fixture
    load_accounts(nested_session.connection())
    data = {'email': 'verysimple@gmail.com'}
    response = api_client.post('/api/v1/signins', json=data)
    s = nested_session.query(Signin).first()
    assert s.email=='verysimple@gmail.com'

@pytest.mark.skip('Use to populated and dump db with signin data.')
def test_dump_signins(dump_signins, nested_session):
    connection = nested_session.connection()
    dump_signins(connection)

def test_can_load_signins_from_dump(load_signins, nested_session):
    connection = nested_session.connection()
    load_signins(connection)
    acc = nested_session.query(Account).filter_by(email='verysimple@gmail.com').one()
    signin = nested_session.query(Signin).filter_by(email='verysimple@gmail.com').one()
    assert acc.email==signin.email

@pytest.fixture
def logins(provider, json):
    def fnc(session):
        signins = session.query(Signin).all()
        return [{
            'provider': provider,
            # we first stringify the json object (i.e. the dict) then we url
            # encode it and that's what becomes the token's payload.
            'token': parse.quote(json.dumps({
                'signin_id': s.signin_id,
                'passcode': s.passcode,
            }))

        } for s in signins]
    return fnc

def test_can_get_access_key_from_passcode_login(
    api_client, logins, load_signins, nested_session, logger, jsloads):
    load_signins(nested_session.connection())
    login_params = logins(nested_session)
    response = api_client.get('/api/v1/access-key', query_string=login_params[0])
    data = jsloads(response.data)
    assert 'access_key' in data
    ak = nested_session.query(AccountAccessKey).filter_by(
        key=data['access_key']).all()
    assert len(ak)==1

# this mostly checks that the fixtures are consistent
def test_can_get_access_key(load_signins, access_key_finder, nested_session):
    load_signins(nested_session.connection())
    access_key = access_key_finder(nested_session, 'verysimple@gmail.com')
    assert access_key
