import pytest
from datetime import datetime as dtm

from b2bapi.db.models.accounts import Account, AccountAccessKey
from b2bapi.db.models.billing import Plan, Billable, BillablePeriod

@pytest.fixture(scope='session')
def provider(): 
    return 'simpleb2b'

@pytest.fixture(scope='session')
def account_email():
    return 'verysimple@gmail.com'

@pytest.fixture(scope='session')
def account_data(provider, account_email):
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
            'email': account_email, 
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
def pricing_plans():
    return [
        {
            'plan_id': 1,
            'name': 'brochure',
            'plan_type': 'domains',
            'cycle': 'monthly',
            'price': 5900,
            'data': {
                'label': {
                    'en': 'Limited brochure',
                    'fr': 'Brochure limitée',
                },
            },
        },
        {
            'plan_id': 2,
            'name': 'portfolio',
            'plan_type': 'domains',
            'cycle': 'monthly',
            'price': 9900,
            'data': {
                'label': {
                    'en': 'Portfolio',
                    'fr': 'Portfolio',
                },
            },
        }
    ]

@pytest.fixture(scope='session')
def domain_data(pricing_plans):
    return [{
        'name': 'lmc',
        # with plan_name
        'plan_name': pricing_plans[-1]['name'],
        #'creation_date': '2019-01-17',
        'data': {
            'label': 'Lao Mountain Coffee',
        }
    },{
        'name': 'greenzone',
        # with plan_id
        'plan_id': pricing_plans[0]['plan_id'],
        #'creation_date': '2018-07-23',
        'data': {
            'label': 'Notepads for Oldskoolers',
        }
    }]

@pytest.fixture(scope='session')
def period_data():
    return [
        # 2018-12
        {
            'start_timestamp': dtm(2018, 12, 3),
            'end_timestamp': dtm(2018, 12, 15),
            'current': False,
        },
        {
            'start_timestamp': dtm(2018, 12, 17),
            'end_timestamp': dtm(2018, 12, 27),
            'current': False,
        },
        # 2019-1
        {
            'start_timestamp': dtm(2019, 1, 2),
            'end_timestamp': dtm(2019, 1, 11),
            'current': False,
        },
        {
            'start_timestamp': dtm(2019, 1, 15),
            'end_timestamp': dtm(2019, 1, 20),
            'current': False,
        },
        {
            'start_timestamp': dtm(2019, 1, 25),
            'end_timestamp': dtm(2019, 1, 31),
            'current': False,
        },
    ]

@pytest.fixture(scope='session')
def signin_data(account_data):
    return [{'email': acc['token']['email']} for acc in account_data]

@pytest.fixture(scope='session')
def dump_accounts(api_client, account_data, db_dump_table):
    """
    Depends:    []
    Dumps:      [accounts, account_access_keys, account_emails]
    """
    def dump(connection):
        [api_client.post('/api/v1/accounts', json=ad) for ad in account_data]
        db_dump_table(connection, table='accounts')
        db_dump_table(connection, table='account_emails')
        db_dump_table(connection, table='account_access_keys')
    return dump


@pytest.fixture(scope='session')
def load_accounts(app, db_load_table):
    """
    Depends:    []
    Loads:      [accounts, account_access_keys, account_emails]
    """
    def load(connection): 
        db_load_table(connection, table='accounts')
        db_load_table(connection, table='account_emails')
        db_load_table(connection, table='account_access_keys')
    return load

@pytest.fixture(scope='session')
def dump_signins(
    load_accounts, api_client, db_dump_table, signin_data):
    """
    Depends:    [accounts, account_access_keys, account_emails]
    Dumps:      [signins]
    """
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
    """
    Depends:    [accounts, account_access_keys, account_emails]
    Loads:      [signins]
    """
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

@pytest.fixture(scope='session')
def dump_pricing(pricing_plans, db_dump_table):
    """
    Depends:    []
    Dumps:      [plans] 
    """
    def dump(session):
        # NOTE: there's no API endpoint for pricing plans yet, so let's use
        # the db session directly.
        [session.add(Plan(**pp)) for pp in pricing_plans]
        session.commit()
        db_dump_table(session.connection(), 'plans')
    return dump

@pytest.fixture(scope='session')
def load_pricing(db_load_table):
    """
    Depends:    []
    Loads:      [plans] 
    """
    def load(connection):
        db_load_table(connection, 'plans')
    return load

@pytest.fixture(scope='session')
def dump_domains(
    load_pricing, load_signins, db_dump_table, api_client, domain_data, 
    auth_headers):
    """
    Depends:    [accounts, account_access_keys, account_emails, signins, plans]
    Dumps:      [billables, domains, billable_periods]
    """
    def dump(session, email):
        # preload db dependencies
        connection = session.connection()
        load_signins(connection)
        load_pricing(connection)
        # populate domains with api endpoint
        auth = auth_headers(session, email)
        [api_client.post('/api/v1/domains', headers=[auth], json=d)
         for d in domain_data]
        connection = session.connection()
        db_dump_table(connection, 'billables')
        db_dump_table(connection, 'domains')
        db_dump_table(connection, 'billable_periods')
    return dump

@pytest.fixture(scope='session')
def load_domains(load_signins, load_pricing, db_load_table):
    """
    Depends:    [accounts, account_access_keys, account_emails, signins, plans]
    Loads:      [billables, domains, billable_periods]
    """
    def load(connection):
        load_signins(connection)
        load_pricing(connection)
        sequence = {'key': 'billables_billable_id_seq',
                    'id': 'billable_id'}
        db_load_table(connection, 'billables', sequence)
        db_load_table(connection, 'domains')
        sequence = {'key': 'billable_periods_billable_period_id_seq',
                    'id': 'billable_period_id'}
        db_load_table(connection, 'billable_periods', sequence)
        pass
    return load

@pytest.fixture(scope='session')
def dump_periods(load_domains, db_dump_table, period_data):
    """
    Depends:    [accounts, account_access_keys, account_emails, signins, plans,
                 billable_periods]
    Dumps:      [billable_periods]
    """
    def dump(session):
        connection = session.connection()
        load_domains(connection)
        for b in session.query(Billable): # same periods each billable, easier to test
            for p_data in period_data:
                period = BillablePeriod(**p_data)
                b.periods.append(period)
        session.commit()
        db_dump_table(session.connection(), 'billable_periods')

    return dump

@pytest.fixture(scope='session')
def load_periods(load_domains):
    """
    Depends:    [accounts, account_access_keys, account_emails, signins, plans, 
                 billable_periods]
    Loads:      []
    """
    def load(connection):
        # load_domains actually already loads billable_periods
        load_domains(connection)
    return load


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
    'domain_data',
    'dump_domains',
    'load_domains',
    'account_email',
    'period_data',
    'dump_periods',
    'load_periods',
]
