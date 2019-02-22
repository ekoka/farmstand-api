import pytest
from b2bapi.db.models.accounts import Account, AccountAccessKey
from b2bapi.db.models.billing import Plan

@pytest.fixture(scope='session')
def provider(): 
    return 'simpleb2b'

@pytest.fixture(scope='session')
def pricing_plans():
    return [
        {
            'plan_id': 1,
            'name': 'limited',
            'plan_type': 'catalog',
            'cycle': 'monthly',
            'price': 5900,
            'details': {
                'label': {
                    'en': 'Limited Catalog',
                    'fr': 'Catalogue Limité',
                },
            },
        },
        {
            'plan_id': 2,
            'name': 'flexible',
            'plan_type': 'catalog',
            'cycle': 'monthly',
            'price': 9900,
            'details': {
                'label': {
                    'en': 'Flexible Catalog',
                    'fr': 'Catalogue Flexible',
                },
            },
        }
    ]

@pytest.fixture(scope='session')
def dump_pricing(pricing_plans, db_dump_table):
    def dump(nested_session):
        [nested_session.add(Plan(**pp)) for pp in pricing_plans]
        nested_session.commit()
        db_dump_table(nested_session.connection(), 'plans')
    return dump

@pytest.fixture(scope='session')
def load_pricing(db_load_table):
    def load(connection):
        db_load_table(connection, 'plans')
    return load

@pytest.fixture(scope='session')
def account_data(provider):
    return [{
        'provider': provider,
        'token': {
            'email': 'someemail@mymail.com', 
            'first_name': 'John',
            'last_name': 'McGee',
            'lang': 'de',
        }
    }, {
        'provider': provider,
        'token': {
            'email': 'verysimple@gmail.com', 
            'first_name': 'mike',
            'last_name': 'ekoka',
            'lang': 'sp',
        }
    }, {
        'provider': provider,
        'token': {
            'email': 'michael@sundry.ca', 
            'first_name': 'M.',
            'last_name': 'Penda',
            'lang': 'en',
        }
    },]


@pytest.fixture(scope='session')
def signin_data(account_data):
    return [{'email': acc['token']['email']} for acc in account_data]

@pytest.fixture(scope='session')
def dump_accounts(api_client, account_data, db_dump_table):
    def dump(connection):
        [api_client.post('/api/v1/accounts', json=ad) for ad in account_data]
        db_dump_table(connection, table='accounts')
        db_dump_table(connection, table='account_emails')
        db_dump_table(connection, table='account_access_keys')
    return dump


@pytest.fixture(scope='session')
def load_accounts(app, db_load_table):
    def load(connection): 
        db_load_table(connection, table='accounts')
        db_load_table(connection, table='account_emails')
        db_load_table(connection, table='account_access_keys')
    return load

@pytest.fixture(scope='session')
def dump_signins(
    load_accounts, api_client, db_dump_table, signin_data):
    def dump(connection):
        # preload accounts
        load_accounts(connection)
        # create signins
        [api_client.post('/api/v1/signins', json=s) for s in signin_data]
        # dump signins
        db_dump_table(connection, table='signins')
    return dump

@pytest.fixture(scope='session')
def load_signins(load_accounts, db_load_table):
    def load(connection):
        load_accounts(connection)
        db_load_table(connection, table='signins')
    return load

@pytest.fixture(scope='session')
def access_key_finder():
    def getfinder(session, email=None):
        acc = session.query(Account).filter_by(email=email).one()
        query = session.query(AccountAccessKey)
        if email:
            return query.filter_by(account_id=acc.account_id).first()
        return query.all()
    return getfinder 

@pytest.fixture(scope='session')
def auth_headers(access_key_finder):
    def httpauth(session, email):
        access_key = access_key_finder(session, email)
        auth_scheme = 'access-token'
        auth = ' '.join([auth_scheme, access_key.key])
        return ('Authorization', auth)
    return httpauth

        

    

__all__ = [
    'provider',
    'account_data',
    'dump_accounts',
    'load_accounts',
    'signin_data',
    'dump_signins',
    'load_signins',
    'access_key_finder',
    'auth_headers',
    'pricing_plans',
    'dump_pricing',
    'load_pricing',
]
