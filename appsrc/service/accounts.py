import jwt
import secrets
import stripe
from flask import current_app as app
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from datetime import datetime, timedelta
#import json
#from urllib import parse

from . import errors as err
from .utils import localize_data
from ..db.models.accounts import Account, AccountEmail, Signin
from ..db.models.domains import Domain
from ..db import db
from ..utils.uuid import clean_uuid
from ..api.routes.routing import api_url

def generate_key(length=24):
    # service
    return secrets.token_urlsafe(length)

"""
- an access key can only be created by providing an authentication token.
- The API only authenticate verified emails, except during registration,
where it provides a temporary token that may not be verified.
- but that token is restricted to creating a new account.
- not accessing existing ones.
"""

def _verify_password_token(data):
    # service
    account = Account.query.join(AccountEmail).filter(
        AccountEmail.email==data['email'], AccountEmail.login==True).first()
    if account and account.authenticate(data['password']):
        return {'email': data['email']}

def create_id_token(data):
    # service
    token_data = _verify_auth_token(data)
    if not token_data:
        raise err.NotAuthorized('Wrong token')
    account_email = (AccountEmail.query
             .filter_by(email=token_data.get('email'), login=True)
             .first())
    if not account_email:
        raise err.NotAuthorized('No email')
    account = account_email.account
    # If we got here, it means that we have indeed verified the token's email.
    # Let's update the account's email.
    account_email.verified = True
    account.confirmed = True
    if not account.id_token:
        account.id_token = generate_key(24)
    db.session.flush()
    return account_email

def generate_token(payload):
    # service
    signature = app.config.SECRET_KEY
    algorithm = 'HS256'
    exp = 3600 # in seconds
    payload.setdefault('exp', datetime.utcnow() + timedelta(seconds=exp))
    #jwt_token = jwt.encode(payload, signature, algorithm).decode('utf-8')
    jwt_token = jwt.encode(payload, signature, algorithm)
    return jwt_token

def generate_access_token(account, domain_name):
    # service
    # default role for account is admin
    role = 'admin'
    account_id = clean_uuid(account.account_id)
    # is user making claim on a domain
    if domain_name:
        try:
            # TODO: Use service from the domains module instead
            domain = Domain.query.filter_by(name=domain_name).one()
        except (orm_exc.NoResultFound, orm_exc.MultipleResultsFound):
            raise err.FormatError('Invalid domain')
        try:
            # TODO Move to global space
            from .domains import get_domain_account
            domain_account = get_domain_account(
                domain_id=domain.domain_id, account_id=account_id)
            if domain_account.active:
                role = domain_account.role or 'user'
        except err.NotFound: pass
    payload = {
        'account_id': account_id,
        'account_url': api_url('api.get_account', account_id=account_id),
        'email': account.email,
        'role': role,
        'domain': domain_name, }
    rv = generate_token(payload)
    return rv

def delete_access_token(access_token):
    # service
    # TODO: should delete from access_tokens table rather than deleting token object.
    db.session.delete(access_token)
    db.session.flush()

def _get_email_registration_data(data):
    # service
    try:
        return {
            'email': data['email'],
            'password': data.get('password') or None,
            'name': data.get('name'),
            'email_verified': False,
            'lang': data.get('lang', 'en'), }
    except: pass

def _verify_email_token(data):
    # service
    """
    Verify, then delete signin token.
    """
    try:
        #data = json.loads(parse.unquote(data))
        signin_id, passcode = data['signin_id'], data['passcode']
    except:
        raise err.FormatError('Invalid token')
    try:
        # Find Signin record.
        s = Signin.query.filter_by(signin_id=signin_id, passcode=passcode).one()
        # If Signin found, delete it.
        db.session.delete(s)
    except orm_exc.NoResultFound as e:
        # if not found raise 404
        raise err.NotAuthenticated('Not authorized')
    return {'email': s.email}

def _verify_auth_token(data):
    # service
    provider, token = data.get('provider', ''), data.get('token', '')
    if not token:
        raise err.FormatError('Missing authentication token')
    if not provider:
        raise err.FormatError('Missing authentication provider')
    rv = None
    if provider==app.config.PROJECT_NAME:
        pwd_auth = 'password' in token
        verify_fnc = _verify_password_token if pwd_auth else _verify_email_token
        rv = verify_fnc(token)
    if not rv:
        raise err.NotAuthenticated('Invalid token')
    return rv

def create_account(data):
    # service
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
        if exists: continue # that id_token exists, get another one.
        account.id_token = id_token
        break
    email = AccountEmail(**{
        'email': account.email,
        # email is marked as verified only if the token says so
        'verified': data['confirmed'],
        'primary': True,
        # enable login attempts with this email in the future
        'login': True, })
    email.account = account
    try:
        create_stripe_customer(account)
        db.session.add(account)
        db.session.flush()
        return account
    except sql_exc.IntegrityError as e:
        db.session.rollback()
        raise err.Conflict('Account already exists')

def create_stripe_customer(account):
    # service
    customer = stripe.Customer.create()
    account.stripe_customer_id = customer['id']

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
def _link_email(email, account): pass


"""
when deleting an email:
    - ensure that it's not the last login email for the account
when setting an email as the primary:
    - ensure that it's a login email
"""
def abort_account_creation(error_code=400, signin_location=None):
    # service
    # this situation should be rare, but just in case
    if signin_location:
        _delete_signin(signin_location)
    header = 'Could not create account.'
    details = {
        400: 'Verify the format of your data.',
        409: 'The Signin option probably already exists. Try logging in instead.', }
    default = details[400]
    message = f'{header}: {details.get(error_code, default)}'
    raise err.ServiceError(error_code, message)

def get_account(account_id):
    # service
    try:
        return Account.query.filter_by(account_id=account_id).one()
    except orm_exc.NoResultFound as e:
        raise err.NotFound('Account not found')
    except orm_exc.MultipleResultsFound as e:
        raise err.NotFound('Account not found')

def update_account(account_id, data, lang):
    # service
    acc = get_account(account_id)
    data['data'] = localize_data(
        data.get('data', {}), fields=Account.localized_fields, lang=lang)
    acc.populate(**data)
    try:
        db.session.flush()
    except sql_exc.IntegrityError:
        db.session.rollback()
        raise err.FormatError('Bad account data')
