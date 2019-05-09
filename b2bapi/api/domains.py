from datetime import datetime as dtm, timedelta
from flask import current_app as app, g
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.utils.uuid import clean_uuid
from b2bapi.db.models.domains import Domain, DomainAccount, DomainAccessRequest
from b2bapi.db.models.accounts import Account
from b2bapi.db.models.billing import Plan
from b2bapi.db import db
from ._route import (
    route, api_url, json_abort, hal,
    domain_owner_authorization as domain_owner_authz,
    account_owner_authorization as account_owner_authz,
)
from b2bapi.db.models.reserved_names import reserved_names
from .utils import localize_data, delocalize_data, StripeContext
from .accounts import _get_account

def _get_plan(plan_id):
    try:
        return Plan.query.filter_by(plan_id=plan_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error': 'Plan not found'})

# the expects_access_token directive also implies authenticate
@route('/domains', methods=['POST'], domained=False, expects_data=True, 
       expects_access_token=True, expects_lang=True)
def post_domain(data, access_token, lang):
    account = _get_account(access_token['account_id'])
    # TODO: validation
    try:
        name = data.pop('name')
    except KeyError:
        json_abort(400, {'error':'Missing catalog identifier'})

    plan = _get_plan(plan_id=data.pop('plan_id', None))

    if not account.stripe_customer_id:
        json_abort(403, {'error': 'Account does not have a linked Stripe '
                         'account'})

    trial_period_days = 30
    trial_end_date = dtm.utcnow() + timedelta(days=trial_period_days)
    month_after_trial = trial_end_date.replace(day=28) + timedelta(days=4)
    #next_month = dtm.now().replace(day=28) + timedelta(days=4)
    billing_cycle_anchor = int(month_after_trial.replace(day=1).timestamp())

    with StripeContext() as ctx:

        def duplicate_nicknames(*a,**kw):
            json_abort(409, {'error': 'The chosen catalog nickname '
                             'is already taken, try a different one.'})
        ctx.register_handler(
            error_type=sql_exc.IntegrityError,
            handler=duplicate_nicknames
        )

        # name the domain
        domain = Domain(name=name)
        # link to account
        domain.owner = account
        # set plan
        domain.plan = plan
        # activate
        domain.active = True
        db.session.add(domain)
        # add detailed information
        if data.get('data'):
            domain.data = localize_data(
                data['data'], Domain.localized_fields, lang)
        domain.meta = data.get('meta') or Domain.default_meta
        db.session.flush()

        # stripe's metadata
        metadata = {
            'domain_id': domain.domain_id,
            'domain_nickname': domain.name,
        }

        # if everything went well, start the meter

        # subscribe customer to plan on stripe
        subscription = ctx.stripe.Subscription.create(
            customer=account.stripe_customer_id,
            items=[{'plan': plan.plan_id}],
            trial_period_days=trial_period_days,
            billing_cycle_anchor=billing_cycle_anchor,
            metadata=metadata,
        )

        # link stripe data to local billable
        domain.subscription_id = subscription.id
        domain.subscription_data = subscription

        # also add a domain_accounts record for owner
        da = _set_domain_account(
            domain_id=domain.domain_id, account_id=account.account_id)
        da.role = 'admin'
        da.active = True

        db.session.flush()

    rv = hal()

    domain_url = api_url('api.get_domain', domain_name=domain.name)
    rv._l('location', domain_url)
    rv._k('domain_name', domain.name)
    return rv.document, 201, [('Location', domain_url)]

def _subscription_data(subscription):
    #TODO
    #"current_period_start": 1552054799,
    #"current_period_end": 1554733199,
    #"status": "active",
    rv = {
        "id": "sub_Ef3fWeFTQIbqr5",
        "billing_cycle_anchor": 1552054799,
        "canceled_at": null,
        "created": 1552054799,
        "quantity": 1,
        "start": 1552054799,
        "tax_percent": null,
        "trial_start": null,
        "trial_end": null,
        "default_source": null,
        "discount": null,
        "ended_at": null,
        "latest_invoice": null,
        "metadata": {},
        "plan": {
            "id": "gold",
            "amount": 2000,
            "currency": "cad",
            "interval": "month",
            "interval_count": 1,
            "nickname": null,
            "product": "prod_BTMywD3UV6AkeY",
            "trial_period_days": null,
        },
    }
    
    return rv


@route('/domains', expects_access_token=True, domained=False, expects_lang=True,
       authorize=account_owner_authz)
def get_domains(access_token, lang):
    account = _get_account(access_token['account_id'])
    rv = hal()
    rv._l('self', api_url('api.get_domains'))

    domains = []
    roles = {}
    for account_domain in account.domains:
        domain = account_domain.domain
        domains.append(_get_domain_resource(domain, lang))
        roles[domain.name] = account_domain.role
    rv._embed('domains', domains)
    rv._k('roles', roles)
    return rv.document, 200, []

def _get_domain_resource(domain, lang):
    domain_url = api_url('api.get_domain', domain_name=domain.name)
    product_schema_url = api_url('api.get_product_schema', domain=domain.name)
    groups_url = api_url('api.get_groups', domain=domain.name)
    group_url = api_url('api.get_group', domain=domain.name, 
                          group_id='{group_id}')
    accounts_url = api_url('api.get_domain_accounts', domain=domain.name)
    account_url = api_url('api.get_domain_account', domain=domain.name,
                          account_id='{account_id}')
    access_requests_url = api_url('api.get_domain_access_requests',
                                  domain=domain.name)
    group_resources_url = api_url(
        'api.get_group_resources', domain=domain.name)
    products_url = api_url('api.get_products', domain=domain.name)
    product_url = api_url('api.get_product', domain=domain.name, 
                          product_id='{product_id}')
    product_json_url = api_url('api.get_product_json', domain=domain.name,
                               product_id='{product_id}')
    product_details_url = api_url('api.get_product_details', domain=domain.name)
    product_resources_url = api_url(
        'api.get_product_resources', domain=domain.name)
    source_images_url = api_url('api.post_source_image', domain=domain.name)
    images_url = api_url('api.get_images', domain=domain.name)
    #inquiries_url = api_url('api.get_inquiries', domain=domain.name)
    rv = hal()._l('self', domain_url)
    rv._k('name', domain.name)
    rv._k('creation_date', domain.creation_date.date())
    rv._l('productlist:product_schema', product_schema_url)
    rv._l('productlist:groups', groups_url)
    rv._l('productlist:domain_accounts', accounts_url)
    rv._l('productlist:domain_account', account_url, unquote=True,
          templated=True)
    rv._l('productlist:domain_access_requests', access_requests_url)
    rv._l('productlist:group_resources', group_resources_url)
    rv._l('productlist:group', group_url, unquote=True, templated=True)
    rv._l('productlist:products', products_url)
    rv._l('productlist:source_images', source_images_url)
    rv._l('productlist:images', images_url)
    #rv._l('productlist:inquiries', inquiries_url)
    rv._l('productlist:product', product_url, unquote=True, templated=True)
    rv._l('productlist:product_json', product_json_url, unquote=True,
          templated=True)
    rv._l('productlist:product_details', product_details_url)
    rv._l('productlist:product_resources', product_resources_url)

    # include company info
    rv._k('data', delocalize_data(domain.data, Domain.localized_fields, lang))
    rv._k('meta', domain.meta)
    return rv.document

def _get_domain(domain_name):
    try:
        return Domain.query.filter_by(name=domain_name).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error_code': 404, 'error': 'Domain not found'})

def _check_domain_ownership(domain_name, **kw):
    account = _get_account(g.access_token['account_id'])
    try:
        domain = Domain.query.filter_by(name=domain_name).one()
    except (orm_exc.NoResultFound, orm_exc.MultipleResultsFound):
        json_abort(404, {'error': 'Domain not found.'})
    domain_account = _get_domain_account(
        domain_id=domain.domain_id, account_id=g.access_token['account_id'])
    return domain_account.active and domain_account.role=='admin'

@route('/domain/<domain_name>', domained=False, expects_lang=True,
       authorize=_check_domain_ownership,)
def get_domain(domain_name, lang):
    domain = _get_domain(domain_name=domain_name)
    return _get_domain_resource(domain, lang), 200, []


@route('/domain/<domain_name>', methods=['put'], domained=False,
       authorize=_check_domain_ownership, expects_lang=True, expects_data=True)
def put_domain(domain_name, data, lang):
    # TODO: validation
    domain = _get_domain(domain_name=domain_name)

    # changing localized data
    domain.data = localize_data(
        data.get('data', {}), Domain.localized_fields, lang)

    # changing metadata
    domain.meta = data.get('meta', {})

    try:
        # only change domain's active state if explicitly set in posted data
        if data['active'] in [True, False]:
            domain.active = data['active']
    except KeyError:
        pass

    db.session.flush()
    return {}, 200, []

@route('/domain-name-check', domained=False, expects_params=True)
def get_domain_name_check(params):
    name = params.get('q')
    if name in reserved_names:
        return {}, 403, []
    try:
        domain = Domain.query.filter(Domain.name==name).one()
        return {}, 200, []
    except orm_exc.NoResultFound as e:
        return {}, 404, []

def _get_domain_account(domain_id, account_id):
    return DomainAccount.query.filter_by(
        domain_id=domain_id, account_id=account_id).one()

def _set_domain_account(domain_id, account_id):
    try:
        return _get_domain_account(domain_id, account_id)
    except orm_exc.NoResultFound: 
        rv = DomainAccount(domain_id=domain_id, account_id=account_id)
        db.session.add(rv)
        db.session.flush()
        return rv


@route('/accounts', methods=['POST'], expects_data=True, expects_domain=True,
       authorize=domain_owner_authz)
def post_domain_account(data, domain):
    # TODO validation
    # TODO: add a routine for user to approve the domain they're being added to
    try:
        da = _set_domain_account(
            domain_id=domain.domain_id, account_id=data['account_id'])
        da.active = True
        da.role = data.get('role', 'user')
        db.session.flush()
    except:
        raise
        db.session.rollback()
        json_abort(400, {'error': 'Could not add account.'})
    return {}, 200, []

@route('/accounts/<account_id>', expects_domain=True, methods=['DELETE'],
       authorize=domain_owner_authz)
def delete_domain_account(account_id, domain):
    try:
        da = _get_domain_account(
            domain_id=domain.domain_id, account_id=account_id)
        da.active = False
    except orm_exc.NoResultFound: 
        db.session.rollback()
    return {}, 200, []

@route('/accounts', expects_domain=True, authorize=domain_owner_authz,
       expects_params=True)
def get_domain_accounts(domain, params):
    q = DomainAccount.query.filter_by(domain_id=domain.domain_id)
    if params.get('active'):
        q = q.filter_by(active=params['active'])
    accounts = q.all()
    rv = hal()
    rv._l('self', api_url('api.get_domain_accounts'))
    rv._embed('accounts', [_get_domain_account_resource(a) for a in accounts])

    return rv.document, 200, []

@route('/accounts/<account_id>', expects_domain=True,
       authorize=domain_owner_authz)
def get_domain_account(domain, account_id):
    try:
        account = _get_domain_account(
            domain_id=domain.domain_id, account_id=account_id)
        rv = _get_domain_account_resource(account)
        return rv, 200, []
    except orm.NoResultFound:
        json_abort(404, {'error': 'Account not found'})

def _get_domain_account_resource(domain_account):
    account = domain_account.account
    resource = hal()
    resource._l('self', api_url(
        'api.get_domain_account', account_id=account.account_id))
    resource._k('account_id', domain_account.account_id)
    resource._k('first_name', account.first_name)
    resource._k('last_name', account.last_name)
    resource._k('email', account.email)
    resource._k('role', domain_account.role)
    resource._k('active', domain_account.active)

    return resource.document

@route('/access-requests', methods=['POST'], expects_data=True, domained=False,
       authenticate=True, expects_account=True)
def post_access_request(account, data):
    try:
        domain = Domain.query.filter_by(name=data.get('domain')).one()
    except orm_exc.NoResultFound:
        json_abort(404, {'error': 'Domain not found.'})
    # TODO validation
    access_request = DomainAccessRequest(
        account_id=account['account_id'],
        domain_id=domain.domain_id,
        creation_date=dtm.utcnow(),
        status="pending",
        data={
            'message': data.get('message'),
            'fields': data.get('fields'),
        },
    )
    db.session.add(access_request)
    try:
        db.session.flush()
    except sql_exc.IntegrityError:
        db.session.rollback()
        json_abort(409, {'error': "Recent access request already exists."})
    rv = hal()
    location = api_url(
        'api.get_access_request', domain_id=domain.domain_id)
    rv._l('location', location)
    return rv.document, 201, [('Location', location)]


@route('/access-requests/<domain_id>', domained=False, expects_account=True,
       authenticate=True)
def get_access_request(domain_id, account):
    try:
        access_request = DomainAccessRequest.query.filter_by(
            domain_id=domain_id, account_id=account.account_id).one()
    except orm_exc.NoResultFound:
        json_abort(404, {'error': 'Access request not found.'})
    except orm_exc.MultipleResultsFound:
        json_abort(409, {'error': 'Multiple access requests found.'})

    rv = hal()
    rv._l('self', api_url('api.get_access_request',
                          domain_id=domain_id))
    rv._k('status', access_request.status)
    rv._k('data', access_request.data)
    rv._k('created', access_request.creation_date)
    return rv.document, 200, []


@route('/access-requests', expects_domain=True, authorize=domain_owner_authz, 
       expects_lang=True)
def get_domain_access_requests(domain, lang):
    rv = hal()
    access_requests = DomainAccessRequest.query.filter_by(
        domain_id=domain.domain_id).all()
    rv._l('self', api_url('api.get_domain_access_requests'))
    rv._l('domain', api_url('api.get_domain', domain_name=domain.name))
    rv._embed('access_requests', [_get_domain_access_request_resources(
        record, lang) for record in access_requests])
    return rv.document, 200, []

@route('/access-requests/<access_request_id>', authorize=domain_owner_authz,
       expects_lang=True)
def get_domain_access_request(access_request_id, lang):
    access_request = _get_access_request(access_request_id)
    document = _get_domain_access_request_resources(access_request, lang)
    return document, 200, []

def _get_domain_access_request_resources(access_request, lang):
    rv = hal()
    rv._l('self', api_url(
        'api.get_domain_access_request', access_request_id=clean_uuid(
            access_request.access_request_id)))
    rv._k('access_request_id', clean_uuid(access_request.access_request_id))
    rv._k('status', access_request.status)
    rv._k('creation_date', access_request.creation_date)
    rv._k('message', access_request.data.get('message'))
    account = access_request.account

    account_data = delocalize_data(
        account.data, account.localized_fields, lang)
    account_resource = dict(
        account_id = account.account_id,
        first_name = account.first_name,
        last_name = account.last_name,
        email = account.primary_email and account.primary_email.email,
    )
    account_resource.update({
        f: account_data.get(f) for f in access_request.data.get('fields', [])
    })
    rv._k('account', account_resource)
    return rv.document

def _get_access_request(access_request_id):
    try:
        return DomainAccessRequest.query.filter_by(
            access_request_id=access_request_id).one()
    except orm_exc.NoResultFound:
        json_abort(404, {'error': 'Access request not found'})

@route('/access-requests/<access_request_id>', methods=['PATCH'],
       expects_data=True, authorize=domain_owner_authz)
def patch_domain_access_request(access_request_id, data):
    # TODO: validation
    access_request = _get_access_request(access_request_id)
    access_request.status = data.get('status')
    return {}, 200, []


