from datetime import datetime as dtm, timedelta
from flask import current_app as app
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db.models.domains import Domain
from b2bapi.db.models.billing import Plan
from b2bapi.db import db
from ._route import route, url_for, json_abort, hal
from b2bapi.db.models.reserved_names import reserved_names
from .utils import localize_data, delocalize_data, StripeContext



def _get_plan(plan_id):
    try:
        return Plan.query.filter_by(plan_id=plan_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error': 'Plan not found'})


@route('/domains', methods=['POST'], domained=False, expects_data=True, 
       expects_account=True, expects_lang=True)
def post_domain(data, account, lang):
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

        # enable domain
        domain.active = True


        db.session.flush()

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

    rv = hal()

    domain_url = url_for('api.get_domain', domain_name=domain.name)
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


@route('/domains', expects_account=True, domained=False, expects_lang=True)
def get_domains(account, lang):
    rv = hal()
    rv._l('self', url_for('api.get_domains'))
    rv._embed('domains', [_get_domain_resource(b, lang)
                          for b in account.billables 
                          if b.plan.plan_type=='domains'])
    return rv.document, 200, []

def _get_domain_resource(domain, lang, partial=False):
    domain_url = url_for('api.get_domain', domain_name=domain.name)
    #account_url = url_for('api.get_account', account_id=domain.account_id)
    product_schema_url = url_for('api.get_product_schema', domain=domain.name)
    filters_url = url_for('api.get_filters', domain=domain.name)
    products_url = url_for('api.get_products', domain=domain.name)
    product_url = url_for('api.get_product', domain=domain.name, 
                          product_id='{product_id}')
    product_json_url = url_for('api.get_product_json', domain=domain.name,
                               product_id='{product_id}')
    product_details_url = url_for('api.get_product_details', domain=domain.name)
    product_resources_url = url_for(
        'api.get_product_resources', domain=domain.name)
    source_images_url = url_for('api.post_source_image', domain=domain.name)
    images_url = url_for('api.get_images', domain=domain.name)
    #inquiries_url = url_for('api.get_inquiries', domain=domain.name)
    rv = hal()._l('self', domain_url)
    rv._k('name', domain.name)
    rv._k('creation_date', domain.creation_date.date())
    #rv._l('productlist:account', account_url)
    rv._l('productlist:product_schema', product_schema_url)
    rv._l('productlist:filters', filters_url)
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

def _get_domain(domain_name, account_id):
    try:
        return Domain.query.filter_by(
            name=domain_name, 
            owner_account_id=account_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error_code': 404, 'error': 'Domain not found'})

@route('/domain/<domain_name>', domained=False, authenticate=True, 
       expects_lang=True, expects_account=True)
def get_domain(domain_name, account, lang):
    domain = _get_domain(
        domain_name=domain_name, account_id=account.account_id)
    return _get_domain_resource(domain, lang), 200, []

@route('/domain/<domain_name>', methods=['put'], domained=False, authenticate=True, 
       expects_lang=True, expects_account=True, expects_data=True)
def put_domain(domain_name, data, account, lang):
    # TODO: validation
    domain = _get_domain(
        domain_name=domain_name, account_id=account.account_id)

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
