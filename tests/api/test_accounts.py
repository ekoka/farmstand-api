import pytest

from b2bapi.db.models.accounts import Account

def test_can_create_account_with_simpleb2b(
    api_client, account_data, nested_session):
    # simpleb2b as provider
    response = api_client.post('/api/v1/accounts', json=account_data)
    acc = nested_session.execute('select * from accounts').fetchone()
    assert acc.email==account_data['token']['email']
    assert acc.lang==account_data['token']['lang']


#def test_dump_accounts(dump_accounts, nested_session):
#    connection = nested_session.connection()
#    dump_accounts(connection)

def test_can_create_signin(load_accounts, nested_session, api_client, logger):
    # preload db with accounts fixture
    load_accounts(nested_session.connection())
    data = {'email': 'verysimple@gmail.com'}
    response = api_client.post('/api/v1/signins', json=data)
    logger.info(response.data)
#def test_can_get_access_key_with_simpleb2b_provider(
#    api_client, load_accounts, nested_session):
#    # get the prophilactic connection  
#    connection = nested_session.connection()
#    # load accounts with the connection
#    load_accounts(connection)
#    acc = nested_session.query(Account).filter_by(
#        email='verysimple@gmail.com').one()
#    assert acc.access_key
#
