import uuid
import os
import shutil
import random
import contextlib
from functools import partial
import simplejson as _json
from  collections import namedtuple
import pytest
import requests

from appsrc.config import test_config as app_config

from appsrc import (make_app, db as _db)
from appsrc.utils.serialize import json_serialize
import appsrc.utils.randomstr

# ensuring that we're only testing from a test database
dbname = app_config.secrets.DB_NAME
app_config.KEEP_TEST_DATABASE = True
assert dbname.startswith('test_') or dbname.endswith('_test')

def cannot_reach_stripe():
    if getattr(cannot_reach_stripe, 'rv', None) is not None:
        return cannot_reach_stripe.rv
    stripe_api = 'https://api.stripe.com/'
    try:
        auth = (app_config.secrets.STRIPE_DEV_KEY,None)
        r = requests.get(stripe_api, timeout=5, auth=auth)
        cannot_reach_stripe.rv = False
    except requests.exceptions.Timeout as e:
        # skip processing here
        cannot_reach_stripe.rv = True
    return cannot_reach_stripe.rv


@pytest.fixture(scope='session')
def db():
    return _db

@pytest.fixture
def db_session(db):
    return db.session

@pytest.fixture(scope='session')
def app(db):
    _app = make_app(app_config)
    with _app.app_context():
        db.drop_all()
        db.create_all()
        ## adding an account


        #db.session.add(Domain(name=, [
        #    {'name': 'domain1'}, {'name': 'domain2'}, {'name': 'domain3'},
        #    {'name': 'domain4'}])
        #db.session.commit()
        # we yield outside the AppContext because keeping it open creates some
        # issues when counting AppContext objects later and it affects the call to
        # do_teardown_appcontext() which in turn is where the db session is
        # registerd for removal.
        yield _app
        # if we want to keep the data we need to commit before closing
        # we need to close the session here, because pytest hangs if there's a
        # floating session somewhere.
        if getattr(app_config, 'KEEP_TEST_DATABASE', None):
            db.session.commit()
            db.session.close()
        else:
            db.session.close()
            db.drop_all()

@pytest.fixture(scope='session')
def json():
    json_nt = namedtuple('json', ('dumps loads'))
    dumps = partial(_json.dumps, default=json_serialize)
    return json_nt(dumps, _json.loads)

@pytest.fixture(scope='session')
def jsloads(json):
    def fnc(x):
        try:
            return json.loads(x)
        except TypeError as e:
            return json.loads(x.decode('utf8'))
    return fnc

@pytest.fixture(scope='session')
def client(app):
    return app.test_client()

@pytest.fixture(scope='session')
def base_url(app):
    return 'https://{server_domain}:{port}'.format(
        server_domain=app.config['SERVER_DOMAIN'],
        port=app.config['HTTP_PORT'],
    )


@pytest.fixture(scope='session')
def logger(app):
    return app.logger

@pytest.fixture(scope='session')
def api_client(client, base_url, logger):
    # create a namedtuple to serve as client
    Client = namedtuple('Client', 'get post put patch delete')
    # api expects json-encoded data
    json_headers = ('Content-Type', 'application/json')

    def req(*a, **kw):
        # args as a list as opposed to a tuple
        a = list(a)
        # path is either specified in kw arg or it's the first item in the
        # args list.
        path = kw.setdefault('path', a.pop(0))
        # method is specified in kw args
        method = kw.pop('method', 'get')
        # if the base_url is already part of the path, ignore its duplicate
        # setting on the client.
        if base_url not in path:
            kw.setdefault('base_url', base_url)
        action = getattr(client, method)
        # if data is being submitted it's in json format.
        # set headers to mark this.
        if method in ('post', 'put', 'patch'):
            kw.setdefault('headers', []).append(json_headers)
        return action(*a, **kw)
    get = partial(req, method='get', )
    post = partial(req, method='post')
    put = partial(req, method='put')
    patch = partial(req, method='patch')
    delete = partial(req, method='delete')
    return Client(get, post, put, patch, delete)

@pytest.fixture
def db_engine(db):
    return db.engine

@pytest.fixture
def db_connection(db_engine):
    return db_engine.connect()

@pytest.fixture
def nested_session(app, db):
    # We first need to isolate a Connection to use to talk to the database
    # during the test, otherwise SQLAlchemy will be the one arbitrarily handing
    # them to its Sessions from its connection Pool. Once a Connection isolated
    # we can have more control over which channel we want the data to travel
    # through.
    conn = db.engine.connect()
    # Next we begin a prophylactic Transaction on that Connection, the purpose
    # of which is to provide a virtual environment for your code to interact
    # with and then to roll back all the changes, leaving the database in its
    # initial state.
    #
    # One more thing to note is that this is not a `SessionTransaction`, which
    # are a logical emulation of the "transaction" concept, a specific
    # capability of SQLAlchemy. `SessionTransactions` are used and managed by
    # `Sessions` at the Python level, whereas a transaction started on a
    # Connection is managed at the database level, so your RDBMS must support
    # that feature well. If you're using Postgresql you're covered.
    wrapper_trans = conn.begin()

    # Let's back up our current Session as we'll not be using it for the
    # duration of the test.
    old_session = db.session

    # Enable a flag to signal if the test is still running (or has ended).
    test_is_running = True

    """
    This function creates a `scoped_session` and binds it to the `Connection` we previously isolated from the engine. It then ties that session to the global db (`SQLAlchemy` object from
    Flask-SQLAlchemy) such that when invoking `db.session` we'll
    """
    def create_nested_session():
        from sqlalchemy import event
        db.session = db.create_scoped_session({'bind': conn, 'binds':{}})
        # start the savepoint
        db.session.begin_nested()
        #listen_to_session(db.session)
        @event.listens_for(db.session, 'after_transaction_end')
        def respawn_savepoint(session, transaction):
            # we only respawn for as long as the test is running
            if test_is_running:
                # if it's a savepoint that ends (with rollback, commit, close)
                # we just reopen another.
                if transaction.nested and not transaction.parent.nested:
                    # ensure that state is expired the way
                    # session.commit() at the top level normally does
                    # (optional step)
                    session.expire_all()
                    session.begin_nested()
                else:
                    create_nested_session()

    create_nested_session()

    yield db.session

    # disabling the respawning of transactions
    test_is_running = False

    # teardown
    db.session.remove()
    old_session.remove()
    wrapper_trans.rollback()
    conn.close()

@pytest.fixture('session')
def is_uuid():
    def wrapper(to_test, version=None):
        try:
            return uuid.UUID(str(to_test), version=version)
        except:
            return False
    return wrapper

@pytest.fixture(scope='session')
def test_dir():
    return os.path.abspath(os.path.dirname(__file__))

@pytest.fixture(scope='session')
def data_fixture_path(test_dir):
    return os.path.join(test_dir, 'data')


@pytest.fixture(scope='session')
def db_load_table(data_fixture_path):
    def load(connection, table, sequence=False):
        # a subtransaction on our transaction at the db level
        transaction = connection.begin()
        cursor = connection.connection.cursor()
        table_csv = os.path.join(data_fixture_path, 'csv', f'{table}.csv')
        sql = f"""
        COPY {table}
        FROM stdin
        WITH (FORMAT csv, DELIMITER ',', HEADER);
        """

        sequence_stmt = "SELECT setval('{key}', (SELECT MAX({id}) FROM {table}));"
        with open(os.path.join(table_csv)) as f:
            #cursor.copy_from(file=f, table='accounts',sep=',')
            cursor.copy_expert(sql, file=f)
            # because we're operating on the direct db connection
        if sequence:
            connection.execute(sequence_stmt.format(table=table, **sequence))
        transaction.commit()
    return load

@pytest.fixture(scope='session')
def db_dump_table(data_fixture_path):
    def dump(connection, table):
        #connection = db.engine.connect().connection

        # a subtransaction on our transaction at the db level
        #transaction = connection.begin()
        cursor = connection.connection.cursor()
        table_csv = os.path.join(data_fixture_path, 'csv', f'{table}.csv')
        sql = """
        COPY {table}
        TO stdout
        WITH (FORMAT csv, DELIMITER ',', HEADER);
        """
        with open(os.path.join(table_csv), 'w') as f:
            #cursor.copy_from(file=f, table='accounts',sep=',')
            cursor.copy_expert(sql.format(table=table), file=f)
            # because we're operating on the direct db connection
            #transaction.commit()
    return dump

from .insert_data import *
