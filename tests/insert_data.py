import pytest


@pytest.fixture
def account_data():
    return [{
        'provider': 'simpleb2b',
        'token': {
            'email': 'someemail@mymail.com', 
            'first_name': 'John',
            'last_name': 'McGee',
            'lang': 'de',
        }
    }, {
        'provider': 'simpleb2b',
        'token': {
            'email': 'verysimple@gmail.com', 
            'first_name': 'mike',
            'last_name': 'ekoka',
            'lang': 'sp',
        }
    }, {
        'provider': 'simpleb2b',
        'token': {
            'email': 'michael@sundry.ca', 
            'first_name': 'M.',
            'last_name': 'Penda',
            'lang': 'en',
        }
    },]


@pytest.fixture
def dump_accounts(api_client, account_data, db_dump_table, logger):
    def dump(connection):
        for ad in account_data:
            resp = api_client.post('/api/v1/accounts', json=ad)
        db_dump_table(connection, table='accounts')
        db_dump_table(connection, table='account_emails')
        db_dump_table(connection, table='account_access_keys')
        db_dump_table(connection, table='signins')
    return dump


@pytest.fixture
def load_accounts(app, db_load_table):
    def load(connection): 
        db_load_table(connection, table='accounts')
        db_load_table(connection, table='account_emails')
        db_load_table(connection, table='account_access_keys')
        db_load_table(connection, table='signins')
    return load


__all__ = [
    'account_data',
    'dump_accounts',
    'load_accounts',
]
