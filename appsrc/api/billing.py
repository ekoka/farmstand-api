from .routes.routing import api_url, hal
from .utils import run_or_abort
from ..service import billing as bill_srv

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
    # api
    fnc = lambda: bill_srv.get_plan(plan_id)
    plan = run_or_abort(fnc)
    return _plan_resource(plan, lang), 200, []

def get_plans(params, lang):
    # api
    fnc = lambda: bill_srv.get_plans()
    plans = run_or_abort(fnc)
    rv = hal()
    rv._l('self', api_url('api.get_plans'))
    rv._embed('plans', [_plan_resource(p, lang) for p in plans])
    return rv.document, 200, []

def get_usage(access_token, year, month):
    # api
    # validate month and year
    # calculate month's daily charges
    # get all periods usage and associated charges
    rv = hal()
    rv._link('self', api_url('api.get_usage'))

def post_payment_source(access_token, data):
    # api
    account_id = access_token['account_id']
    token = data['token']
    fnc = bill_srv.add_payment_source(account_id, token)
    run_or_abort(fnc)
    return {}, 200, []

def get_payment_sources(access_token):
    # api
    account_id = access_token['account_id']
    fnc = bill_srv.get_payment_sources(account_id)
    payment_sources = run_or_abort(fnc)
    rv = hal()
    rv._l('self', api_url('api.get_payment_sources'))
    rv._l('payment_source', api_url(
        'api.delete_payment_source', source_id='{source_id}'),
          templated=True, unquote=True)
    rv._k('sources', [_get_payment_source_data(s) for s in payment_sources])
    return rv.document, 200, []

def _get_payment_source_data(source):
    # api
    fields = ('brand', 'last4', 'exp_year', 'exp_month', 'address_zip')
    rv = {f: source.data.get(f) for f in fields}
    rv['source_id'] = source.source_id
    rv['default_source'] = source.default_source
    return rv

def delete_payment_source(source_id, access_token):
    # api
    account_id = access_token['account_id']
    fnc = lambda: bill_srv.delete_payment_source(account_id, source_id)
    run_or_abort(fnc)
    return {}, 200, []
