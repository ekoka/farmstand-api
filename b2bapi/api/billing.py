from flask import g, abort, current_app as app, jsonify, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err
import slugify
from datetime import datetime as dtm, timedelta
from functools import reduce

from ..db.models.domains import Domain
from ..db.models.billing import Plan, Billable
from ..db.models.accounts import PaymentSource
from ..db import db
from ..utils.uuid import clean_uuid
from .routes.routing import api_url, json_abort, hal
from .utils import localize_data, delocalize_data, StripeContext

from .accounts import _get_account

def _plan_resource(p, lang):
    rv = hal()
    rv._l('self', api_url('api.get_plan', plan_id=p.plan_id))
    rv._k('plan_id', p.plan_id)
    rv._k('data', p.data)
    #rv._k('name', p.name)
    #rv._k('price', p.price)
    #rv._k('cycle', p.cycle)
    #rv._k('plan_type', p.plan_type)
    #rv._k('data', delocalize_data(p.data, Plan.localized_fields, lang))
    return rv.document

def get_plan(plan_id, lang):
    try:
        plan = Plan.query.filter_by(plan_id=plan_id).one()
    except (orm_exc.NoResultFound):
        json_abort(404, {'error': 'Plan not found.'})
    return _plan_resource(plan, lang), 200, []

def get_plans(params, lang):
    plans = Plan.query.all()
    plans = sorted(plans, key= lambda p: p.data.get('amount', 0))
    rv = hal()
    rv._l('self', api_url('api.get_plans'))
    rv._embed('plans', [_plan_resource(p, lang) for p in plans])
    return rv.document, 200, []

def get_usage(access_token, year, month):
    # validate month and year
    # calculate month's daily charges

    # get all periods usage and associated charges

    rv = hal()
    rv._link('self', api_url('api.get_usage'))

def post_payment_source(access_token, data):
    #TODO: validation
    # data = payment_source.validate(data)
    token = data['token']

    account = _get_account(access_token['account_id'])

    with StripeContext() as ctx:
        customer = ctx.stripe.Customer.retrieve(account.stripe_customer_id)
        source = customer.sources.create(source=token['id'])
        customer.refresh()
        account.payment_sources.append(PaymentSource(
            source_id=source.id,
            data=source,
            default_source=customer.default_source==source.id,
        ))
        db.session.flush()
    return {}, 200, []

def get_payment_sources(access_token):
    sources = PaymentSource.query.filter_by(
        account_id=access_token['account_id']).all()
    rv = hal()
    rv._l('self', api_url('api.get_payment_sources'))
    rv._l('payment_source', api_url(
        'api.delete_payment_source', source_id='{source_id}'), templated=True,
        unquote=True)
    rv._k('sources', [_get_source_data(s) for s in sources])
    return rv.document, 200, []

def _get_source_data(source):
    fields = ['brand', 'last4', 'exp_year', 'exp_month',
              'address_zip']
    rv = {f: source.data.get(f) for f in fields}
    rv['source_id'] = source.source_id
    rv['default_source'] = source.default_source
    return rv

def delete_payment_source(source_id, access_token):
    account = _get_account(access_token['account_id'])
    sources = PaymentSource.query.filter_by(
        account_id=access_token['account_id']).all()

    with StripeContext() as ctx:
        customer = ctx.stripe.Customer.retrieve(account.stripe_customer_id)
        customer.sources.retrieve(source_id).delete()
        customer.refresh()
        for s in sources:
            if s.source_id==source_id:
                db.session.delete(s)
            else:
                s.default_source = s.source_id==customer.default_source
    return {}, 200, []
