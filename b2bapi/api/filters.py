import uuid
import simplejson as json

from flask import redirect, g, current_app as app, abort, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db import db
from b2bapi.db.models.filters import (
    Filter, ProductFilter as PFilter, FilterSet as FSet)
from ._route import route, hal, json_abort

def _create_filter_sets(tenant_id):
    categories = FilterSet(tenant_id=tenant_id)
    categories.data = {
        'label': {'en': 'Categories', 'fr': 'Catégories'},
        'multichoice': True,
    }
    brands = FilterSet(tenant_id=tenant_id)
    brands.data = {
        'label': {'en': 'Brands', 'fr': 'Marques'},
        'multichoice': False,
    }
    db.session.add(categories)
    db.session.add(brands)
    db.session.flush()
    return [categories, brands]

@route('/filter-sets', expects_tenant=True)
def get_filter_sets(tenant):
    tenant_id = tenant.tenant_id
    fsets = FSet.query.filter_by(tenant_id=tenant_id).all()
    if not fsets:
        fsets = _create_filter_sets(tenant.tenant_id)

    rv = hal() 
    rv._l('self', url_for('api.get_filter_sets'))
    rv._l('find', url_for(
        'api.get_filter_set', filter_set_id='{filter_set_id}'), unquote=True,
        templated=True)
    # rv._l('simpleb2b:filters', url_for('api.post_filters'))
    rv._l('simpleb2b:filter', url_for(
        'api.get_filter', filter_id='{filter_id}'), unquote=True,
        templated=True)

    rv._embed('filter_sets',[
        _get_filter_set_resource(fs, partial=False) for fs in  fsets
    ])

    return rv.document, 200, []

def _get_filter_set_resource(fs, partial=False):
    rv = hal()
    rv._l('self', url_for(
        'api.get_filter_set', filter_set_id=fs.filter_set_id))
    #rv._l('simpleb2b:filters', url_for(
    #    'api.post_filter', filter_set_id=fs.filter_set_id))
    rv._k('filter_set_id', fs.filter_set_id)
    rv._k('label', fs.data.setdefault('label', {'en':None}).get('en'))
    rv._k('multichoice', fs.data.setdefault('multichoice', True))
    if not partial:
        rv._embed('filters', [
            _get_filter_resource(f, partial=True) for f in fs.filters])
    return rv.document

@route('/filter-sets/<filter_set_id>')
def get_filter_set(filter_set_id):
    pass

@route('/filter-sets/<filter_set_id>', methods=['POST'], expects_data=True,
       expects_tenant=True)
def post_filter(filter_set_id, data, tenant):
    try:
        fs = FSet.query.filter_by(
            filter_set_id=filter_set_id,
            tenant_id=tenant.tenant_id).one()
    except:
        json_abort(404, {'error': 'Filter Set Not Found'})

    # TODO: validate to remove filter_id, parent_id from meta
    f = Filter()
    # the remainder should go into JSON data field
    #for k,v in data.items():
    #    f.data[k] = v
    # limit the data to 'label' for now, with language set to 'en'
    f.data = {'label': {'en': data.get('label'), 'fr': None}}
    fs.filters.append(f)
    try:
        db.session.flush()
    except sql_exc.IntegrityError:
        db.session.rollback()
        json_abort(400, {})
    rv = hal()
    status_code = 201
    location =  url_for('api.get_filter', filter_id=f.filter_id)
    rv._k('status_code', status_code)
    rv._k('status', 'created')
    rv._l('location', location)
    rv._embed('resource', _get_filter_resource(f, partial=True))
    return rv.document, status_code, [('Location', location)]

def _get_filter_resource(f, partial=False):
    rv = hal()
    rv._l('self', url_for('api.get_filter', filter_id=f.filter_id))
    rv._k('filter_id', f.filter_id)
    rv._k('label', f.data.setdefault('label',{'en':None}).get('en'))
    if f.parent:
        rv._embed('parent', _get_filter_resource(f.parent, partial=True))
    if partial:
        rv._k('partial', True)
    else:
        rv._k('level', f.level)
        rv._embed('filter_set', _get_filter_set_resource(f.filter_set, partial=True))
        rv._l('simpleb2b:products', url_for('api.get_products', filter=f.filter_id))
    return rv.document

@route('/filters/<filter_id>', expects_tenant=True)
def get_filter(filter_id, tenant):
    try:
        f = Filter.query.filter_by(
            filter_id=filter_id, tenant_id=tenant.tenant_id).one()
    except:
        json_abort(404)
    rv = _get_filter_resource(f, partial=False)
    return rv, 200, []

@route('/filters/<filter_id>', methods=['PUT'], expects_data=True, 
       authenticate=True)
def put_filter(filter_id, data):
    try:
        f = Filter.query.filter_by(filter_id=filter_id).one()
    except:
        json_abort(404)
    f.data.setdefault(
        'label', {'en':None, 'fr':None})['en'] = data.get('label')
    try:
        db.session.flush()
    except:
        db.session.rollback()
        json_abort(400)
    return {}, 200, []


@route('/filters/<filter_id>', methods=['DELETE'], authenticate=True,
       expects_tenant=True)
def delete_filter(filter_id, tenant):
    db.session.execute(
        'DELETE FROM filters WHERE tenant_id=:tenant_id '
        'AND filter_id=:filter_id',
        {'tenant_id':tenant.tenant_id, 'filter_id':filter_id})
    return {}, 200, []


#@route('/products/<product_id>', methods=['DELETE'])
#def delete_product(product_id):
#    try:
#        p = _get_product(product_id)
#        db.session.delete(p)
#        db.session.flush()
#        #.products.delete().where(
#        #    (products.c.tenant_id==g.tenant['tenant_id'])&
#        #    (products.c.product_id==product_id)))
#    except:
#        pass
#    return ({}, 200, [])
#
