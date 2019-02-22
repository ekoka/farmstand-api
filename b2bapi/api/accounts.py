import secrets
from flask import g, abort, current_app as app, jsonify, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err
from datetime import datetime
import json
from urllib import parse

from b2bapi.db.models.accounts import (
    Account, AccountEmail, AccountAccessKey, Signin) #, Profile)
from b2bapi.db import db
from .domains import _get_domain_resource
from b2bapi.utils.uuid import clean_uuid
from b2bapi.utils.randomstr import randomstr
#from b2bapi.utils.hal import Resource as Hal
from .validation.accounts import new_account
from ._route import route, hal, json_abort

from b2bapi.utils.gauth import GAuth
   
def generate_key(length=24):
    return secrets.token_urlsafe(length)


def create_access_key(account_id, reset=False):
    db.session.execute(
        'delete from account_access_keys where account_id=:account_id',
        {'account_id': account_id})
    return AccountAccessKey(key=generate_key(24), account_id=account_id)


"""
- an access key can only be created by providing an authentication token.
- simpleauth only authenticate verified emails, except during registration,
where it provides a temporary token that may not be verified.
- but that token is restricted to creating a new account.
- not accessing existing ones.
"""
@route('/access-key', methods=['PUT'], domained=False, expects_data=True)
def put_access_key(data):
    token_data = _verify_auth_token(data)
    if not token_data:
        return {'error': 'Invalid token'}, 400, []

    # only authenticate verified emails.
    #if not token_data.get('email_verified', False):
    #    return {'error': 'Email not verified'}, 400, []

    # use a login email account (login=True)
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

    # if we got here it means we have indeed verified the token's email
    # let's update our account's email 
    email.verified = True
    email.account.confirmed = True

    try:
        email.account.access_key = create_access_key(email.account.account_id)
    except sql_exc.IntegrityError as e:
        db.session.rollback()
        return {
            'error': 'Could not create key. Try again later.'
        }, 409, []

    db.session.flush()
    access_key = email.account.access_key

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
        'key': access_key.key
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

@route('/access-key', domained=False, expects_params=True)
def get_access_key(params):
    token_data = _verify_auth_token(params)
    if not token_data:
        json_abort(400, {'error': 'Invalid token'})

    # find email record, with login authorization
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
                    #'simpleb2b:account-create': url_for('api.post_account'),
                },
                   
            },
            'error': 'Account not found'
        }, 404, []

    # if we got here it means we have indeed verified the token's email
    # let's update our account's email 
    email.verified = True
    email.account.confirmed = True
    db.session.flush()

    try:
         rv = _access_key(email.account.access_key)
    except:
        # we should normally never end here as an account should always have
        # an access_key, but just in case the key was somehow deleted, let's
        # put things back into a more stable state.
        email.account.access_key = create_access_key(email.account.account_id)
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
@route('/accounts', methods=['POST'], domained=False, expects_data=True)
def post_account(data):
    try:
        provider, token = data['provider'], data['token']
        if provider.lower()=='google':
            token_data = _verify_google_token(token)
        elif provider.lower()=='simpleb2b':
            token_data = _get_email_registration_data(token)
        else:
            token_data = None
    except:
        token_data = None

    if not token_data:
        json_abort(400, {'error': 'Invalid token'})

    def _rv(account_id): 
        #TODO get curies from config     
        rv = hal()
        rv._l('location', url_for('api.get_account', account_id=account_id))
        rv._l('simpleb2b:access_key', url_for('api.get_access_key'))
        return rv.document

    #app.logger.info(db.session.connection())
    try:
        # create account, account_email and access_key
        account = create_account_from_token(token_data)
        return _rv(account.account_id), 201, []
    except sql_exc.IntegrityError as e:
        email = AccountEmail.query.filter_by(
            email=token_data.get('email')).first()
        doc =  _rv(email.account_id)
        doc['error'] = 'Email already registered.'
        return doc, 409, []


def _get_email_registration_data(data):
    try:
        return {
            'email': data['email'],
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'email_verified': False,
            'lang': data.get('lang', 'en'),
        }
    except:
        pass


def _verify_email_token(data):
    try:
        data = json.loads(parse.unquote(data))
        signin_id, passcode = data['signin_id'], data['passcode']
    except:
        json_abort(400, {'error': 'Invalid token'})

    try:
        # find Signin record
        s = Signin.query.filter_by(
            signin_id=signin_id, 
            passcode=passcode,
        ).one()
    except orm_exc.NoResultFound as e:
        # if not found raise 404
        json_abort(404, {'error': 'Passcode not found'})

    # if Signin found, login is successful, delete Signin
    db.session.delete(s)
    return {'email': s.email}


def _verify_google_token(token):
    ggauth = GAuth(
        client_id=app.config['GOOGLE_CLIENT_ID'], 
        secret=app.config['GOOGLE_SECRET'], 
        redirect_uri=app.config['GOOGLE_REDIRECT_URI'])
    return ggauth.verify_token(token)


def _verify_auth_token(data):
    provider, token = data.get('provider'), data.get('token')

    if not token:
        json_abort(400, {'error':'Missing authentication token'})

    if not provider:
        json_abort(400, {'error': 'Missing authentication provider'})

    if provider.lower()=='google':
        app.logger.info(token)
        return _verify_google_token(token)

    elif provider.lower()=='simpleb2b':
        return _verify_email_token(token)
    else:
        json_abort(400, {'error': 'Unrecognized authentication provider'})


def create_account_from_token(profile):
    account = Account(**{
        'first_name': profile.get('given_name') or profile.get('first_name'),
        'last_name': profile.get('family_name') or profile.get('last_name'),
        'email': profile['email'],
        'confirmed': profile.get('email_verified', False),
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

    access_key = AccountAccessKey(**{
        'key': generate_key(24),
    })

    account.access_key = access_key
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

@route('/accounts/<account_id>', domained=False, authenticate=True)
def get_account(account_id):
    self = url_for('api.get_account', account_id=account_id)
    a = Account.query.get(account_id) 
    return _get_account_resource(a), 200, []


def _get_account_resource(account, partial=False):
    a = account
    rv = hal()
    rv._l('self', url_for('api.get_account', account_id=account.account_id))
    rv._k('account_id',account.account_id)
    rv._k('first_name', account.first_name)
    rv._k('last_name', account.last_name)

    #if account.domain:
    #    rv._l('simpleb2b:domain', url_for(
    #        'api.get_domain', tname=account.domain.name))
    #    rv._embed('domain', _get_domain_resource(account.domain, partial=True))
    domains = [_get_domain_resource(domain.domain, partial=True) 
               for domain in account.domains]
    rv._k('roles', {d.domain.name:d.role for d in account.domains})
    rv._embed('domains', [_get_domain_resource(domain.domain, partial=True)
                          for domain in account.domains])

    if partial:
        rv._k('primary_email', account.email)
        return rv.document

    rv._k('emails', [{
        'email':e.email, 
        'verified': e.verified, 
        'primary':e.primary} for e in account.emails])

    return rv.document

