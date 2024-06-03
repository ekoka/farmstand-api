from flask import current_app as app, url_for

from ..db.models.accounts import Account
from .service import account as acc_srv
from .validation import accounts as val
from .routes.routing import hal, json_abort, api_url
from .utils import delocalize_data, run_or_abort

"""
- an access key can only be created by providing an authentication token.
- The API only authenticate verified emails, except during registration,
where it provides a temporary token that may not be verified.
- but that token is restricted to creating a new account.
- not accessing existing ones.
"""

def post_id_token(data):
    # api
    """
    ID Token is the token provided during registration by either the OAuth
    authority or by the API (for email auth, or password auth).
    """
    fnc = lambda: create_id_token(data)
    account_email = run_or_abort(fnc)
    account = account_email.account
    rv = hal()
    rv._l('self', api_url('api.post_id_token'))
    rv._l(f'{app.config.API_NAMESPACE}:account', api_url(
        'api.get_account', account_id=account.account_id))
    rv._k('token', account.id_token)
    return rv.document, 200, []

def post_access_token(data, account):
    # api
    fnc = lambda: acc_srv.generate_access_token(data, account)
    token = run_or_abort(fnc)
    rv = hal()
    rv._l('self', api_url('api.post_access_token'))
    rv._k('token', token)
    return rv.document, 200, []

def get_profile(access_token):
    # api
    """
    The difference between this resource and `account` is that this
    one returns the authenticated user's profile, whereas `account` returns
    the account info that matches the url's `account_id`.
    That means that this resource can effectively only be retrieved by the
    profile's owner and its full url can be published as part of the `Root`
    resource.
    """
    rv = hal()
    rv._l('self', api_url('api.get_profile'))
    rv._l(f'{app.config.API_NAMESPACE}:account', api_url(
        'api.get_account', account_id=access_token['account_id']))
    rv._k('account_id', access_token['account_id'])
    return rv.document, 200, []

def delete_access_token(access_token):
    # api
    fnc = lambda: acc_srv.delete_access_token(access_token)
    run_or_abort(fnc)
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
    # api
    token_data = None
    try:
        provider, token = data.get('provider','').lower(), data.get('token', '')
        #if provider=='google':
        #    # first fetch the data from google
        #    token_data = _verify_google_token(token)
        #    # next normalize data to fit the rest of the flow
        #    token_data = val.new_account_via_google.validate(token_data)
        if provider==app.config.PROJECT_NAME:
            # validate + normalize
            token_data = val.new_account_via_email.validate(token)
            #token_data = _get_email_registration_data(token)
    except:
        pass
    if not token_data:
        json_abort(400, {'error': 'Invalid token'})
    # create account, account_email and id_token
    fnc = lambda: acc_srv.create_account(token_data)
    account = run_or_abort(fnc)
    rv = hal()
    rv._l('location', api_url('api.get_account', account_id=account.account_id))
    rv._l(f'{app.config.API_NAMESPACE}:access_token', api_url('api.post_access_token'))
    return rv.document, 201, []


def get_account(account_id, lang):
    # api
    fnc = lambda: acc_srv.get_account(account_id)
    acc = run_or_abort(fnc)
    return _get_account_resource(acc, lang=lang), 200, []

def _get_account_resource(account, lang, partial=False):
    # api - resource
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
    domains = [_get_domain_resource(domain.domain, lang,) for domain in account.domains]
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
    # api
    data = val.edit_account.validate(data)
    fnc = lambda: acc_srv.update_account(account_id, data, lang)
    run_or_abort(fnc)
    return {}, 200, []
