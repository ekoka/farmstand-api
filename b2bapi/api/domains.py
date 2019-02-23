from flask import g, abort, current_app as app, jsonify, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err
import slugify
from datetime import datetime as dtm 

from b2bapi.db.models.domains import Domain
from b2bapi.db.models.billing import Plan, Billable, BillablePeriod
from b2bapi.db import db
from b2bapi.utils.uuid import clean_uuid
from ._route import route, url_for, json_abort, hal
from b2bapi.db.models.reserved_names import reserved_names



def _get_plan(plan_id=None, plan_name=None):
    filter_by = {'name': plan_name} if plan_id is None else {'plan_id': plan_id}
    try:
        return Plan.query.filter_by(**filter_by).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error': 'Plan not found'})


@route('/domains', methods=['POST'], domained=False, expects_data=True, 
       expects_account=True)
def post_domain(data, account):
    # TODO: validation
    try:
        name = data.pop('name')
    except KeyError:
        json_abort(400, {'error':'Missing catalog identifier'})

    plan = _get_plan(plan_id=data.pop('plan_id', None), 
                     plan_name=data.pop('plan_name', None))
        
    try:
        # name the domain
        domain = Domain(name=name)
        # add detailed information
        domain.data = data.get('details') or {}
        # link the plan
        domain.plan = plan
        # record the pricing and billing cycle
        domain.recorded_price = plan.price
        domain.recorded_cycle = plan.cycle
        # set the owner account
        domain.owner = account
        # enable domain
        domain.active = True
        # start the meter
        domain.init_period()
        # try flushing to the db
        db.session.add(domain)
        db.session.flush()
    except sql_exc.IntegrityError as e:
        db.session.rollback()
        json_abort(409, {
            'error': f'The chosen catalog identifier "{name}"'
            ' is already taken, try a different one.'})

    #domain_resource = _get_domain_resource(domain, partial=True)
    #domain_url = domain_resource['_links']['self']['href']
    rv = hal()

    domain_url = url_for('api.get_domain', domain_name=domain.name)
    rv._l('location', domain_url)
    #rv._embed('domain', _get_domain_resource(domain, partial=True))
    return rv.document, 201, [('Location', domain_url)]


def set_billable_period(billable):
    periods = billable.recent_periods
    bp = _start_billable_period(billable)
    return bp

@route('/domains', expects_account=True, domained=False)
def get_domains(account):
    rv = hal()
    rv._l('self', url_for('api.get_domains'))
    rv._embed('domains', [_get_domain_resource(b)
                          for b in account.billables 
                          if b.plan.plan_type=='domains'])
    return rv.document, 200, []

def _get_domain_resource(domain, partial=False):
    domain_url = url_for('api.get_domain', domain_name=domain.name)
    #account_url = url_for('api.get_account', account_id=domain.account_id)
    product_schema_url = url_for('api.get_product_schema', domain=domain.name)
    filters_url = url_for('api.get_filters', domain=domain.name)
    products_url = url_for('api.get_products', domain=domain.name)
    product_url = url_for('api.get_product', domain=domain.name, 
                          product_id='{product_id}')
    product_details_url = url_for('api.get_product_details', domain=domain.name)
    source_images_url = url_for('api.post_source_image', domain=domain.name)
    images_url = url_for('api.get_images', domain=domain.name)
    #inquiries_url = url_for('api.get_inquiries', domain=domain.name)
    rv = hal()._l('self', domain_url)
    rv._k('name', domain.name)
    #rv._l('simpleb2b:account', account_url)
    rv._l('simpleb2b:product_schema', product_schema_url)
    rv._l('simpleb2b:filters', filters_url)
    rv._l('simpleb2b:products', products_url)
    rv._l('simpleb2b:source_images', source_images_url)
    rv._l('simpleb2b:images', images_url)
    #rv._l('simpleb2b:inquiries', inquiries_url)
    rv._l('simpleb2b:product', product_url, unquote=True, templated=True )
    rv._l('simpleb2b:product_details', product_details_url)
    if partial:
        return rv._k('_partial', True).document

    # include company info
    for k,v in domain.data.items():
        rv._k(k, v)

    return rv.document

@route('/domain/<domain_name>', domained=False, authenticate=True)
def get_domain(domain_name):
    try:
        domain = Domain.query.filter(Domain.name==domain_name).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error_code': 404, 'error': 'Domain not found'})
    return _get_domain_resource(domain), 200, []

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
