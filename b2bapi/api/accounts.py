import secrets
from flask import g, abort, current_app as app, jsonify, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db.models.signins import Signin
from b2bapi.db.models.accounts import (
    Account, AccountEmail, AccountAccessKey) #, Profile)
from b2bapi.db import db
from b2bapi.utils.uuid import clean_uuid
from b2bapi.utils.randomstr import randomstr
#from b2bapi.utils.hal import Resource as Hal
from .validation.accounts import new_account
from ._route import route, hal

from b2bapi.utils.gauth import GAuth
   
def logger(*a, **kw):
    return app.config['LOGGER'].info(*a, **kw)


def generate_key(length=24):
    return secrets.token_urlsafe(length)


def create_access_key(account, reset=False):
    db.session.execute(
        'delete from account_access_keys where account_id=:account_id',
        {'account_id': account.account_id})
    account.access_key = AccountAccessKey(key=generate_key(24))
    db.session.flush()

"""
- an access key can only be created by providing an authentication token.
- simpleauth only authenticate verified emails, except during registration,
where it provides a temporary token that may not be verified.
- but that token is restricted to creating a new account.
- not accessing existing ones.
"""
@route('/access-key', methods=['PUT'], tenanted=False, expects_data=True)
def put_access_key(data):
    token_data = _verify_auth_token(data)
    if not token_data:
        return {'error': 'Invalid token'}, 401, []

    # only authenticate verified emails.
    if not token_data.get('email_verified', False):
        return {'error': 'Email not verified'}, 401, []

    email = AccountEmail.query.filter_by(
        email=token_data.get('email'), login=True).first()

    if not email:
        return {
            '_links': {
                'curies': [{
                    'name': 'simpleb2b',
                    'templated': True,
                    'href': 'https://api.simpleb2b.io/docs/{rel}'
                }],
                'self': {
                    'href': url_for('api.get_access_key'),
                },
                'simpleb2b:account-create': {
                    'href': url_for('api.post_account'),
                },
                   
            },
            'error': 'Account not found',
        }, 404, []

    # only authenticate into account if email was given login permission 
    if not email.login:
        return {'error': 'Email not authorized for authentication'}, 401, []

    # if we got here it means we have indeed verified the token's email
    # let's update our account's email 
    email.verified = True

    try:
        create_access_key(email.account)
    except sql_exc.IntegrityError as e:
        db.session.rollback()
        return {
            'error': 'Could not create key. Try again later.'
        }, 409, []

    db.session.flush()

    return {
        '_links': {
            'curies': [{
                'name': 'simpleb2b',
                'templated': True,
                'href': 'https://api.simpleb2b.io/docs/{rel}'
            }],
            'self': {
                'href': url_for('api.get_access_key'),
            },
            'simpleb2b:account': {
                'href': url_for('api.get_account', account_id=email.account_id),
            },
        },
        'key': email.account.access_key.key
    }, 200, []


def _access_key(access_key):
    return {
        '_links': {
            'curies': [{
                'name': 'simpleb2b',
                'templated': True,
                'href': 'https://api.simpleb2b.io/docs/{rel}'
            }],
            'self': {
                'href': url_for('api.get_access_key'),
            },
            'simpleb2b:account': {
                'href': url_for('api.get_account', account_id=access_key.account_id),
            },
        },
        'access_key': access_key.key
    }

@route('/access-key', tenanted=False, expects_params=True)
def get_access_key(params):
    token_data = _verify_auth_token(params)
    if not token_data:
        return {'error': 'Invalid token'}, 401, []

    # only authenticate verified emails.
    if not token_data.get('email_verified', False):
        return {'error': 'Email not verified'}, 401, []

    email = AccountEmail.query.filter_by(
        email=token_data.get('email'), login=True).first()

    if not email:
        return {
            '_links': {
                'curies': [{
                    'name': 'simpleb2b',
                    'templated': True,
                    'href': 'https://api.simpleb2b.io/docs/{rel}'
                }],
                'self': {
                    'href': url_for('api.get_access_key'),
                    'simpleb2b:account-create': url_for('api.post_account'),
                },
                   
            },
            'error': 'Account not found'
        }, 404, []

    # only authenticate into account if email was given login permission 
    if not email.login:
        return {'error': 'Email not authorized for authentication'}, 401, []

    # if we got here it means we have indeed verified the token's email
    # let's update our account's email 
    email.verified = True
    db.session.flush()

    try:
         rv = _access_key(email.account.access_key)
    except:
        # we should normally never end here, but just in case the key was
        # somehow deleted, let's put things back into a more stable state
        create_access_key(email.account)
        rv = _access_key(email.account.access_key)

    return rv, 200, []

"""
token may contain an unconfirmed email
if that email is already present in the system:
    the bearer is required to verify the email and try to login
else (if email is not already in the system):
    an account is created

in any case an account is only created if the email does not exist
"""
@route('/accounts', methods=['POST'], tenanted=False, expects_data=True)
def post_account(data):
    token_data = _verify_auth_token(data)
    if not token_data:
        return {'error': 'Invalid token'}, 401, []

    def _rv(_acc, _code): 
        return ({
            '_links': {
                'curies': [{
                    'name': 'simpleb2b',
                    'href': 'https://api.simpleb2b.io/docs/{rel}',
                    'templated': True,
                }],
                'location': {'href': url_for(
                    'api.get_account', account_id=_acc.account_id)},
                'simpleb2b:access_key': {'href': url_for('api.get_access_key')}
            },
            '_embedded': {
                'access_key':_access_key(_acc.access_key),
            },
            'access_key': _acc.access_key.key,
        }, _code, [])

    try:
        account = create_account_from_auth_token(token_data)
        return _rv(account, 201)
    except sql_exc.IntegrityError as e:
        email = AccountEmail.query.filter_by(
            email=token_data.get('email')).first()
        doc, code, headers =  _rv(email.account, 409)
        doc['error'] = 'Existing account.'
        return doc, code, headers

def _verify_auth_token(data):
    ggauth = GAuth(
        client_id=app.config['GOOGLE_CLIENT_ID'], 
        secret=app.config['GOOGLE_SECRET'], 
        redirect_uri=app.config['GOOGLE_REDIRECT_URI'])
    if not data.get('token'):
        json_abort(401, {'error':'Missing authentication token'})

    if not data.get('provider'):
        abort(401, 'Missing authentication provider')

    if data['provider'].lower()=='google':
        return ggauth.verify_token(data['token'])
    elif data['provider'].lower()=='simpleb2b':
        #token_expr = {"tokens": [{"type": "activation_token", 
        #                        "status": "active"}]}
        token_expr = {"tokens": [{
            "token": data['token'], 
            "status": "pending",
            "type": "activation_token",
        }]}
        s = Signin.query.filter(
            Signin.meta.comparator.contains(token_expr)).one()
        for t in s.meta['tokens']:
            if t['type']=='activation_token' and t['token']==data['token']:
                t['status'] = 'active'
        return {
            'email': s.email, 
            'first_name': s.data.get('first_name'),
            'last_name': s.data.get('last_name'),
            'lang': s.data.get('lang', 'en'),
            'email_verified': True,
        }
        # TODO add sbauth as an auth provider
        # return sbauth.verify_token(data['token'])
        pass
    else:
        abort(401, 'Unrecognized authentication provider')


def create_account_from_auth_token(profile):
    account = Account(**{
        'first_name': profile.get('given_name') or profile.get('first_name'),
        'last_name': profile.get('family_name') or profile.get('last_name'),
        'email': profile['email'],
        'lang': profile.get('locale', None) or profile.get('lang', 'en'),
    })
    email = AccountEmail(**{
        'email': account.email,
        # email is marked as verified only if the token says so
        'verified': profile.get('email_verified', False),
        'primary': True,
        # enable login attempts with this email in the future
        'login': True, 
    })
    #profile = Profile(**{
    #    'profile_name': 'default',
    #    'first_name': account.first_name,
    #    'last_name': account.last_name,
    #})
    access_key = AccountAccessKey(**{
        'key': generate_key(24),
    })

    account.access_key = access_key
    #profile.email = email
    email.account = account

    try:
        db.session.add(account)
        db.session.flush()
        return account
    except sql_exc.IntegrityError as e:
        db.session.rollback()
        raise

"""
user may request for email to be linked
    - email is added to list of unverified emails for this account
    - email pending confirmation have no use, other than
        - showing user which emails they requested to be linked
        - signaling the system which emails should be sent a confirmation url

an email may be linked to an account:
    - only if it's not already in use
    - only if it's been confirmed (verified)

when confirming an email later:
    - it should not already be present in the table of confirmed emails
    whether for this account or another.
"""
def _link_email(email, account):
    pass


"""
when deleting an email:
    - ensure that it's not the last login email for the account
when setting an email as the primary:
    - ensure that it's a login email
"""

def abort_account_creation(error_code=400, signin_location=None):
    # this situation should be rare, but just in case
    if signin_location:
        _delete_signin(signin_location)

    message = 'Could not create account.'
    details = {
        400: 'Verify the format of your data.',
        409: ('The Signin option probably already exists. '
              'Try logging in instead.'),
    }
    default = details[400]
    resp = jsonify({
        'error': message, 
        'details':details.get(error_code, default)
    })
    resp.status_code = error_code
    abort(resp)

@route('/accounts/<account_id>', methods=['GET'], tenanted=False)
def get_account(account_id):
    self = url_for('api.get_account', account_id=account_id)
    a = Account.query.get(account_id) 
    return _get_account_resource(a), 200, []


def _get_account_resource(account, partial=False):
    from .tenants import _get_tenant_resource
    a = account
    rv = hal()
    rv._l('self', url_for('api.get_account', account_id=account.account_id))
    rv._k('account_id',account.account_id)
    rv._k('first_name', account.first_name)
    rv._k('last_name', account.last_name)

    if account.tenant:
        rv._l('simpleb2b:tenant', url_for(
            'api.get_tenant', tname=account.tenant.name))
        rv._embed('tenant', _get_tenant_resource(account.tenant, partial=True))

    if partial:
        rv._k('primary_email', account.email)
        return rv.document

    rv._k('emails', [{
        'email':e.email, 
        'verified': e.verified, 
        'primary':e.primary} for e in account.emails])

    return rv.document

def _verify_signin_token(token):
    #TODO
    return True
