from flask import g, abort, current_app as app, jsonify, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err
import slugify

from b2bapi.db.models.tenants import Tenant
from b2bapi.db import db
from b2bapi.utils.uuid import clean_uuid
from ._route import route, url_for, json_abort, hal


@route('/tenants', methods=['POST'], tenanted=False, expects_data=True, 
       expects_account=True)
def post_tenant(data, account):
    # TODO: validation
    tenant = account.tenant
    if tenant:
        tenant_url = url_for('api.get_tenant', tname=tenant.name)
        account_url = url_for('api.get_account', account_id=account.account_id)
        rv = hal()._k('error_code', 409)
        rv._k('error', 'company already registered')
        rv._l('location', tenant_url)
        rv._l('account', account_url)
        rv._embed('tenant', _get_tenant_resource(tenant, partial=True))
            
        return rv.document, 409, []

    try:
        name = data.pop('name')
    except KeyError:
        json_abort(400, {'error':'Missing company identifier', 'field': 'name'})

    try:
        tenant = Tenant(name=name)
        tenant.data = data
        tenant.account = account
        db.session.add(tenant)
        db.session.flush()
    except sql_exc.IntegrityError as e:
        db.session.rollback()
        json_abort(409, {
            'error': f'The chosen company identifier "{name}"'
            ' is already taken, try a different one.'})

    #tenant_resource = _get_tenant_resource(tenant, partial=True)
    #tenant_url = tenant_resource['_links']['self']['href']
    rv = hal()

    tenant_url = url_for('api.get_tenant', tname=tenant.name)
    rv._l('location', tenant_url)
    #rv._embed('tenant', _get_tenant_resource(tenant, partial=True))
    return rv.document, 201, [('Location', tenant_url)]


def _get_tenant_resource(tenant, partial=False):
    tenant_url = url_for('api.get_tenant', tname=tenant.name)
    #account_url = url_for('api.get_account', account_id=tenant.account_id)
    product_schema_url = url_for('api.get_product_schema', tenant=tenant.name)
    filters_url = url_for('api.get_filters', tenant=tenant.name)
    products_url = url_for('api.get_products', tenant=tenant.name)
    product_url = url_for('api.get_product', tenant=tenant.name, 
                          product_id='{product_id}')
    product_details_url = url_for('api.get_product_details', tenant=tenant.name)
    source_images_url = url_for('api.post_source_image', tenant=tenant.name)
    images_url = url_for('api.get_images', tenant=tenant.name)
    #inquiries_url = url_for('api.get_inquiries', tenant=tenant.name)
    rv = hal()._l('self', tenant_url)
    rv._k('name', tenant.name)
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
    for k,v in tenant.data.items():
        rv._k(k, v)

    return rv.document

@route('/tenant-name-search', expects_params=True, tenanted=False)
def get_tenant_name_search(name):
    try:
        Tenant.query.filter(Tenant.name==name).one()
        return {}, 200, []
    except:
        return {}, 404, []


@route('/tenant/<tname>', tenanted=False)
def get_tenant(tname):
    try:
        tenant = Tenant.query.filter(Tenant.name==tname).one()
    except:
        raise
        json_abort(404, {'error_code': 404, 'error': 'Tenant not found'})
    return _get_tenant_resource(tenant), 200, []
