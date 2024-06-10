import jwt
import secrets
from flask import g, abort, current_app as app, jsonify, url_for, request
import stripe
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from datetime import datetime, timedelta
import json
from urllib import parse

from ..db.models.accounts import Account, AccountEmail, AccountAccessKey, Signin #, Profile
from ..db.models.domains import Domain
from ..db import db
from ..utils.uuid import clean_uuid
from ..utils.randomstr import randomstr
from .validation import accounts as val
from .routes.routing import hal, json_abort, api_url
from .utils import localize_data, delocalize_data

def generate_key(length=24):
    return secrets.token_urlsafe(length)

"""
- an access key can only be created by providing an authentication token.
- The API only authenticate verified emails, except during registration,
where it provides a temporary token that may not be verified.
- but that token is restricted to creating a new account.
- not accessing existing ones.
"""

def _verify_password_token(data):
    account = Account.query.join(AccountEmail).filter(
        AccountEmail.email==data['email'], AccountEmail.login==True).first()
    if not account:
        return
    if account.authenticate(data['password']):
        return {'email': data['email']}

def post_id_token(data):
    """
    ID Token is the token provided during registration by either the OAuth
    authority or by the API (for email auth, or password auth).
    """
    token_data = _verify_auth_token(data)
    if not token_data:
        json_abort(401, {'error': 'Not authorized (wrong token)'})
    email = AccountEmail.query.filter_by(
        email=token_data.get('email'), login=True).first()
    if not email:
        json_abort(401, {'error': 'Not authorized (no email)'})
    account = email.account
    # if we got here it means we have indeed verified the token's email
    # let's update our account's email
    email.verified = True
    account.confirmed = True
    if not account.id_token:
        account.id_token = generate_key(24)
    db.session.flush()
    rv = hal()
    rv._l('self', api_url('api.post_id_token'))
    rv._l(f'{app.config.API_NAMESPACE}:account', api_url(
        'api.get_account', account_id=account.account_id))
    rv._k('token', account.id_token)
    return rv.document, 200, []

def generate_token(payload):
    signature = app.config.SECRET_KEY
    algorithm = 'HS256'
    exp = 3600 # in seconds
    payload.setdefault('exp', datetime.utcnow() + timedelta(seconds=exp))
    #jwt_token = jwt.encode(payload, signature, algorithm).decode('utf-8')
    jwt_token = jwt.encode(payload, signature, algorithm)
    return jwt_token

def post_access_token(data, account):
    # default role for account is admin
    role = 'admin'
    # is user making claim on a domain
    domain_name = data.get('domain')
    if domain_name:
        try:
            domain = Domain.query.filter_by(name=domain_name).one()
        except (orm_exc.NoResultFound, orm_exc.MultipleResultsFound):
            json_abort(404, {'error': 'Domain not found'})

        try:
            from .domains import _get_domain_account
            domain_account = _get_domain_account(
                domain_id=domain.domain_id, account_id=account.account_id)
            if domain_account.active:
                role = domain_account.role or 'user'
        except (orm_exc.NoResultFound, orm_exc.MultipleResultsFound):
            pass

    payload = {
        'account_id': clean_uuid(account.account_id),
        'account_url': api_url(
            'api.get_account', account_id=clean_uuid(account.account_id)),
        'email': account.email,
        'role': role,
        'domain': domain_name,
    }
    token = generate_token(payload)
    rv = hal()
    rv._l('self', api_url('api.post_access_token'))
    rv._k('token', token)
    return rv.document, 200, []


def get_profile(access_token):
    """
    The difference between this resource and `account` is that this
    one returns the authenticated user's profile, whereas `account` returns
    the account info that matches the url's `account_id`.
    That means that this resource can effectively only be retrieved by the
    account's owner and its full url can be published as part of the `Root`
    resource.
    """
    rv = hal()
    rv._l('self', api_url('api.get_profile'))
    rv._l(f'{app.config.API_NAMESPACE}:account', api_url(
        'api.get_account', account_id=access_token['account_id']))
    rv._k('account_id', access_token['account_id'])
    return rv.document, 200, []


def delete_access_token(access_token):
    db.session.delete(access_token)
    db.session.flush()
    return {}, 200, []

"""
token may contain an unconfirmed email
if that email is already present in the system:
    the bearer is required to verify the email and try to login
else (if email is not already in the system):
    an account is created

in any case an account is only created if the email does not exist
"""
def post_account(data):
    token_data = None
    try:
        provider, token = data.get('provider','').lower(), data.get('token', '')
        if provider=='google':
            # first fetch the data from google
            token_data = _verify_google_token(token)
            # next normalize data to fit the rest of the flow
            token_data = val.new_account_via_google.validate(token_data)
        if provider==app.config.PROJECT_NAME:
            # validate + normalize
            token_data = val.new_account_via_email.validate(token)
            #token_data = _get_email_registration_data(token)
    except:
        raise
    if not token_data:
        json_abort(400, {'error': 'Invalid token'})
    try:
        # create account, account_email and id_token
        account = create_account_from_token(token_data)
    except sql_exc.IntegrityError as e:
        json_abort(409, {'error': 'Account already exists'})
    rv = hal()
    rv._l('location', api_url('api.get_account', account_id=account.account_id))
    rv._l(f'{app.config.API_NAMESPACE}:access_token', api_url('api.post_access_token'))
    return rv.document, 201, []


def _get_email_registration_data(data):
    try:
        return {
            'email': data['email'],
            'password': data.get('password') or None,
            'name': data.get('name'),
            'email_verified': False,
            'lang': data.get('lang', 'en'),
        }
    except:
        pass


def _verify_email_token(data):
    try:
        #data = json.loads(parse.unquote(data))
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
        json_abort(401, {'error': 'Not authorized'})
    # if Signin found, login is successful, delete Signin
    db.session.delete(s)
    return {'email': s.email}

def _verify_auth_token(data):
    provider, token = data.get('provider', ''), data.get('token', '')
    if not token:
        json_abort(400, {'error':'Missing authentication token'})
    if not provider:
        json_abort(400, {'error': 'Missing authentication provider'})
    rv = None
    if provider==app.config.PROJECT_NAME:
        verify_fnc = _verify_password_token if 'password' in token else _verify_email_token
        rv = verify_fnc(token)
    return rv or json_abort(401, {'error': 'Not authorized (invalid token)'})


def create_account_from_token(data):
    # validated fields:
    # name,  email, email_verified,
    # lang, locale, password
    #data['name'] = data.pop('name') or data['name']
    #data['lang'] = data.pop('locale') or data['lang']
    #data['confirmed'] = data.pop('

    account = Account(**data)

    while True:
        id_token = generate_key(24)
        exists = Account.query.filter_by(id_token=id_token).first()
        if exists:
            # that id_token exists, get another one
            continue
        account.id_token = id_token
        break

    email = AccountEmail(**{
        'email': account.email,
        # email is marked as verified only if the token says so
        'verified': data['confirmed'],
        'primary': True,
        # enable login attempts with this email in the future
        'login': True,
    })

    email.account = account

    try:
        create_stripe_customer(account)
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

def _get_account(account_id):
    try:
        return Account.query.filter_by(account_id=account_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error': 'Account not found'})
    except orm_exc.MultipleResultsFound as e:
        json_abort(404, {'error': 'Ambiguous results.'})


def get_account(account_id, lang):
    self = api_url('api.get_account', account_id=account_id)
    a = _get_account(account_id)
    return _get_account_resource(a, lang=lang), 200, []


def _get_account_resource(account, lang, partial=False):
    a = account
    rv = hal()
    rv._l('self', api_url('api.get_account', account_id=account.account_id))
    rv._l('domains', api_url('api.get_domains'))
    rv._l('payment_sources', api_url('api.post_payment_source'))

    rv._l('payment_source', api_url(
        'api.delete_payment_source', source_id='{source_id}'), templated=True,
        unquote=True)
    # TODO maybe namespace domains url with acccount_id
    # rv._l('domains', url_for('api.get_domains', account_id=account.account_id))
    rv._k('account_id',account.account_id)
    rv._k('name', account.name)

    from .domains import _get_domain_resource
    domains = [_get_domain_resource(domain.domain, lang,)
               for domain in account.domains]
    rv._k('roles', {d.domain.name:d.role for d in account.domains})
    rv._embed('domains', domains)

    rv._k('data', delocalize_data(
        account.data, Account.localized_fields, lang))
    rv._k('emails', [{
        'email':e.email,
        'verified': e.verified,
        'primary':e.primary} for e in account.emails])

    return rv.document

def put_account(account_id, data, lang):
    #TODO: data validation
    data = val.edit_account.validate(data)
    a = _get_account(account_id)
    data['data'] = localize_data(
        data.get('data', {}), fields=Account.localized_fields, lang=lang)
    a.populate(**data)
    try:
        db.session.flush()
    except sql_exc.IntegrityError:
        db.session.rollback()
        json_abort(400, {'error': 'Bad format'})
    return {}, 200, []

def create_stripe_customer(account):
    customer = stripe.Customer.create()
    account.stripe_customer_id = customer['id']
