import uuid
import simplejson as json

from flask import redirect, g, current_app as app, abort, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db import db
from b2bapi.utils.uuid import clean_uuid
from b2bapi.db.models.filters import (
    Filter, FilterOption, ProductFilterOption as PFOption)
from ._route import route, hal, json_abort
from .product_utils import _localize_data, _merge_localized_data, _delocalize_data

@route('/filters', expects_tenant=True, expects_lang=True, authenticate=True)
def get_filters(lang, tenant):
    filters = Filter.query.filter_by(tenant_id=tenant.tenant_id).all()
    rv = hal()
    rv._l('self', url_for('api.get_filters'))
    rv._l('filter', url_for('api.get_filter', filter_id='{filter_id}'),
                            templated=True, unquote=True)
    rv._k('filter_ids', [f.filter_id for f in filters])
    rv._embed('filters', [_filter_resource(f, lang, partial=True) 
                          for f in filters])
    return rv.document, 200, []

# TODO: review
@route('/filters', methods=['POST'], expects_tenant=True, expects_data=True,
       expects_lang=True, authenticate=True)
def post_filter(data, lang, tenant):
    #TODO: validate
    # data = val.new_filter.validate(data)

    f = Filter( tenant_id=tenant.tenant_id)
    f.data = _localize_data(data['data'], ['label', 'description'], lang)
    f.active = data['active']
    f.multichoice = data['multichoice']
    db.session.add(f)

    try:
        db.session.flush()
    except:
        db.session.rollback()
        json_abort(400, {'error': 'Bad format'})


    if data.get('options'):
        _sync_options(f, data['options'], lang, tenant.tenant_id)
    rv = hal()
    location = url_for('api.get_filter', filter_id=f.filter_id)
    rv._l('location', location)
    rv._k('filter_id', f.filter_id)
    return rv.document, 201, [('Location', location)]

def _sync_options(f, options, lang, tenant_id):
    # first, find all options that did not make it
    try:
        new_option_ids = set(
            [clean_uuid(o['filter_option_id']) for o in options if o.get('filter_option_id')])
        existing_option_ids = set([clean_uuid(o.filter_option_id) for o in f.options])
    except:
        db.session.rollback()
        json_abort(400, {'error': 'filter_option_id has an invalid UUID format'})

    deleted = tuple(existing_option_ids.difference(new_option_ids))
    # delete all relations to products
    if deleted:
        clause = db.text(
            'delete from products_filter_options '
            'where tenant_id=:tenant_id '
            'and filter_option_id in :optionlist'
        )
        delete_product_options = clause.bindparams(tenant_id=tenant_id, optionlist=deleted)
        db.session.execute(delete_product_options)
        # delete options
        clause = db.text(
            'delete from filter_options '
            'where tenant_id=:tenant_id '
            'and filter_option_id in :optionlist'
        )
        delete_options = clause.bindparams(tenant_id=tenant_id, optionlist=deleted)
        db.session.execute(delete_options)
    # update the remaining existing options
    for position,o in enumerate(options):
        # if the option has an id it needs to be updated
        if o.get('filter_option_id'):
            try:
                # go through existing options
                for fp in f.options:
                    # and find the corresponding option
                    if clean_uuid(fp.filter_option_id)==clean_uuid(o['filter_option_id']):
                        # update position
                        fp.position = position
                        # merge data
                        _merge_localized_data(
                            fp.data, o.get('data', {}), ['label'], lang)
            except IndexError:
                db.session.rollback()
                json_abort(400, {'error': 'Invalid filter_option_id'})
        # if option does not have an id it needs to be added
        else:
            try:
                # new option
                fp = FilterOption(
                    tenant_id=tenant_id, 
                    position=position,
                )
                # localize the data
                fp.data = _localize_data(
                    o.get('data', {}), ['label'], lang)
                # add to filter
                f.options.append(fp)
            except:
                db.session.rollback()
                json_abort(400, {'error': 'Bad format'})

@route('/filters/<filter_id>', methods=['PUT'], expects_data=True, 
       expects_lang=True, expects_tenant=True, authenticate=True)
def put_filter(filter_id, data, lang, tenant):
    #TODO: validate
    # data = val.edit_filter.validate(data)
    f = _get_filter(filter_id, tenant.tenant_id)
    _merge_localized_data(f.data, data.pop('data'), ['label', 'description'], lang)
    f.active = data.get('active', False)
    f.multichoice = data.get('multichoice', False)
    _sync_options(f, data.get('options', []), lang, tenant.tenant_id)
    # TODO: process options in bulk
    try:
        db.session.flush()
    except:
        db.session.rollback()
        json_abort(400, {'error': 'Bad format'})
    return {}, 200, []

def _get_filter(filter_id, tenant_id):
    try:
        return Filter.query.filter_by(
            filter_id=filter_id, 
            tenant_id=tenant_id
        ).one()
    except: 
        json_abort(404, {'error': 'Filter not found'})

def _filter_resource(f, lang, partial=False):
    rv = hal()
    rv._l('self', url_for('api.get_filter', filter_id=f.filter_id))
    if not partial:
        rv._l('options', url_for('api.post_filter_option', filter_id=f.filter_id))
        rv._l('option', url_for('api.get_filter_option', filter_id=f.filter_id,
                                filter_option_id='{filter_option_id}'),
                                templated=True, unquote=True)
    rv._k('filter_id', f.filter_id)
    rv._k('active', f.active)
    rv._k('multichoice', f.multichoice)
    rv._k('data', _delocalize_data(f.data, ['label', 'description'], lang))
    rv._k('options', [{
        'data': _delocalize_data(o.data, ['label'], lang),  
        'filter_option_id': clean_uuid(o.filter_option_id)} for o in f.options])
    return rv.document

@route('/filters/<filter_id>', expects_tenant=True, expects_lang=True,
       authenticate=True)
def get_filter(filter_id, lang, tenant):
    f = _get_filter(filter_id, tenant.tenant_id)
    rv = _filter_resource(f, lang, partial=False)
    return rv, 200, []

@route('/filters/<filter_id>', methods=['DELETE'], expects_tenant=True,
       authenticate=True)
def delete_filter(filter_id, tenant):
    try:
        db.session.execute(
            'DELETE FROM filters WHERE tenant_id=:tenant_id ' 
            'AND filter_id=:filter_id ',
            {
                'tenant_id':tenant.tenant_id, 
                'filter_id':filter_id,
            })
    except: 
        db.session.rollback()
    return {}, 200, []


def _filter_option_resource(filter_option, lang):
    f_o = filter_option
    rv = hal()
    rv._l('self', url_for('api.get_filter_option', filter_id=f_o.filter_id,
                          filter_option_id=f_o.filter_option_id))
    rv._l('products', url_for(
        'api.put_filter_option_products', filter_id=f_o.filter_id,
        filter_option_id=f_o.filter_option_id))
    #if not partial:
    #    rv._l('filter', url_for('api.get_filter', filter_id=f_o.filter_id))
    rv._k('filter_option_id', f_o.filter_option_id)
    rv._k('data', _delocalize_data(f_o.data, ['label'], lang))
    rv._k('products', [p.product_id for p in filter_option.products])
    return rv.document

@route('/filters/<filter_id>/options', methods=['POST'], expects_lang=True,
       expects_tenant=True, expects_data=True, authenticate=True)
def post_filter_option(filter_id, data, lang, tenant):
    # TODO: validation
    # data = val.new_filter_option(data)
    f_o = FilterOption(tenant_id=tenant.tenant_id, filter_id=filter_id)
    f_o.data = _localize_data(data, ['label'], lang)
    db.session.add(f_o)
    try:
        db.session.flush()
    except: 
        db.session.rollback()
        json_abort(400, {'error': 'Bad format'})
    rv = hal()
    location = url_for('api.get_filter_option', filter_id=filter_id, 
                       filter_option_id=f_o.filter_option_id)
    rv._l('location', location)


def _get_filter_option(filter_id, filter_option_id, tenant_id):
    try:
        f_o = FilterOption.query.filter(
            FilterOption.filter_id==filter_id, 
            FilterOption.filter_option_id==filter_option_id,
            FilterOption.tenant_id==tenant_id).one()
        return f_o
    except:
        json_abort(404, {'error': 'Filter option not found'})

@route('/filters/<filter_id>/options/<filter_option_id>', authenticate=True,
       expects_tenant=True, expects_lang=True)
def get_filter_option(filter_id, filter_option_id, lang, tenant):
    f_o = _get_filter_option(filter_id, filter_option_id, tenant.tenant_id)
    rv = _filter_option_resource(f_o, lang)
    return rv, 200, []

@route('/filters/<filter_id>/options/<filter_option_id>', authenticate=True,
       expects_tenant=True, expects_lang=True, expects_data=True)
def put_filter_option(filter_id, filter_option_id, data, lang, tenant):
    # TODO: validate
    # data = val.filter_option.validate(data)
    f_o = _get_filter_option(filter_id, filter_option_id, tenant.tenant_id)
    _merge_localized_data(f_o.data, data['data'], ['label'], lang)
    try:
        db.session.flush()
    except:
        json_abort(400, {'error': 'Bad format'})
    return {}, 200, []

@route('/filters/<filter_id>/options/<filter_option_id>', authenticate=True,
       expects_tenant=True)
def delete_filter_option(filter_id, filter_option_id, tenant):
    try:
        db.session.execute(
            'DELETE FROM filter_options WHERE tenant_id=:tenant_id ' 
            'AND filter_id=:filter_id '
            'AND filter_option_id=:filter_option_id',
            {
                'tenant_id':tenant.tenant_id, 
                'filter_id':filter_id,
                'filter_option_id':filter_option_id
            })
    except: 
        db.session.rollback()
    return {}, 200, []

@route('/filters/<filter_id>/options/<filter_option_id>/products',
       methods=['PUT'], expects_tenant=True, expects_data=True,
       authenticate=True)
def put_filter_option_products(filter_id, filter_option_id, tenant, data):
    f_o = _get_filter_option(filter_id, filter_option_id, tenant.tenant_id)
    try:
        db.session.execute(
            'DELETE FROM products_filter_options WHERE tenant_id=:tenant_id ' 
            'AND filter_option_id=:filter_option_id',
            {
                'tenant_id':tenant.tenant_id, 
                'filter_option_id':filter_option_id
            })
    except: 
        db.session.rollback()
        raise
        #json_abort(400, {'error': 'Bad format'})

    new = [{
        'tenant_id': tenant.tenant_id, 
        'filter_option_id': filter_option_id, 
        'product_id': product_id} for product_id in data.get('products', [])]

    if new:
        db.session.execute(
            'insert into products_filter_options '
            '(tenant_id, filter_option_id, product_id) values '
            '(:tenant_id, :filter_option_id, :product_id)', new)

    try:
        db.session.flush()
    except:
        db.session.rollback()
    return {}, 200, []


# def _create_filter_sets(tenant_id):
#     categories = FilterSet(tenant_id=tenant_id)
#     categories.data = {
#         'label': {'en': 'Categories', 'fr': 'Catégories'},
#         'multichoice': True,
#     }
#     brands = FilterSet(tenant_id=tenant_id)
#     brands.data = {
#         'label': {'en': 'Brands', 'fr': 'Marques'},
#         'multichoice': False,
#     }
#     db.session.add(categories)
#     db.session.add(brands)
#     db.session.flush()
#     return [categories, brands]
# 
# @route('/filter-sets', expects_tenant=True)
# def get_filter_sets(tenant):
#     tenant_id = tenant.tenant_id
#     fsets = FilterSet.query.filter_by(tenant_id=tenant_id).all()
#     if not fsets:
#         fsets = _create_filter_sets(tenant.tenant_id)
# 
#     rv = hal() 
#     rv._l('self', url_for('api.get_filter_sets'))
#     rv._l('find', url_for(
#         'api.get_filter_set', filter_set_id='{filter_set_id}'), unquote=True,
#         templated=True)
#     # rv._l('simpleb2b:filters', url_for('api.post_filters'))
#     rv._l('simpleb2b:filter', url_for(
#         'api.get_filter', filter_id='{filter_id}'), unquote=True,
#         templated=True)
# 
#     rv._embed('filter_sets',[
#         _get_filter_set_resource(fs, partial=False) for fs in  fsets
#     ])
# 
#     return rv.document, 200, []
# 
# def _get_filter_set_resource(fs, partial=False):
#     rv = hal()
#     rv._l('self', url_for(
#         'api.get_filter_set', filter_set_id=fs.filter_set_id))
#     #rv._l('simpleb2b:filters', url_for(
#     #    'api.post_filter', filter_set_id=fs.filter_set_id))
#     rv._k('filter_set_id', fs.filter_set_id)
#     rv._k('label', fs.data.setdefault('label', {'en':None}).get('en'))
#     rv._k('multichoice', fs.data.setdefault('multichoice', True))
#     if not partial:
#         rv._embed('filters', [
#             _get_filter_resource(f, partial=True) for f in fs.filters])
#     return rv.document
# 
# @route('/filter-sets/<filter_set_id>')
# def get_filter_set(filter_set_id):
#     pass
# 
# @route('/filter-sets/<filter_set_id>', methods=['POST'], expects_data=True,
#        expects_tenant=True)
# def post_filter(filter_set_id, data, tenant):
#     try:
#         fs = FilterSet.query.filter_by(
#             filter_set_id=filter_set_id,
#             tenant_id=tenant.tenant_id).one()
#     except:
#         json_abort(404, {'error': 'Filter Set Not Found'})
# 
#     # TODO: validate to remove filter_id, parent_id from meta
#     f = Filter()
#     # the remainder should go into JSON data field
#     #for k,v in data.items():
#     #    f.data[k] = v
#     # limit the data to 'label' for now, with language set to 'en'
#     f.data = {'label': {'en': data.get('label'), 'fr': None}}
#     fs.filters.append(f)
#     try:
#         db.session.flush()
#     except sql_exc.IntegrityError:
#         db.session.rollback()
#         json_abort(400, {})
#     rv = hal()
#     status_code = 201
#     location =  url_for('api.get_filter', filter_id=f.filter_id)
#     rv._k('status_code', status_code)
#     rv._k('status', 'created')
#     rv._l('location', location)
#     rv._embed('resource', _get_filter_resource(f, partial=True))
#     return rv.document, status_code, [('Location', location)]
# 
# def _get_filter_resource(f, partial=False):
#     rv = hal()
#     rv._l('self', url_for('api.get_filter', filter_id=f.filter_id))
#     rv._k('filter_id', f.filter_id)
#     rv._k('label', f.data.setdefault('label',{'en':None}).get('en'))
#     if f.parent:
#         rv._embed('parent', _get_filter_resource(f.parent, partial=True))
#     if partial:
#         rv._k('partial', True)
#     else:
#         rv._k('level', f.level)
#         rv._embed('filter_set', _get_filter_set_resource(f.filter_set, partial=True))
#         rv._l('simpleb2b:products', url_for('api.get_products', filter=f.filter_id))
#     return rv.document
# 
# @route('/filters/<filter_id>', expects_tenant=True)
# def get_filter(filter_id, tenant):
#     try:
#         f = Filter.query.filter_by(
#             filter_id=filter_id, tenant_id=tenant.tenant_id).one()
#     except:
#         json_abort(404)
#     rv = _get_filter_resource(f, partial=False)
#     return rv, 200, []
# 
# @route('/filters/<filter_id>', methods=['PUT'], expects_data=True, 
#        authenticate=True)
# def put_filter(filter_id, data):
#     try:
#         f = Filter.query.filter_by(filter_id=filter_id).one()
#     except:
#         json_abort(404)
#     f.data.setdefault(
#         'label', {'en':None, 'fr':None})['en'] = data.get('label')
#     try:
#         db.session.flush()
#     except:
#         db.session.rollback()
#         json_abort(400)
#     return {}, 200, []
# 
# 
# @route('/filters/<filter_id>', methods=['DELETE'], authenticate=True,
#        expects_tenant=True)
# def delete_filter(filter_id, tenant):
#     db.session.execute(
#         'DELETE FROM filters WHERE tenant_id=:tenant_id '
#         'AND filter_id=:filter_id',
#         {'tenant_id':tenant.tenant_id, 'filter_id':filter_id})
#     return {}, 200, []
# 
# 
# #@route('/products/<product_id>', methods=['DELETE'])
# #def delete_product(product_id):
# #    try:
# #        p = _get_product(product_id)
# #        db.session.delete(p)
# #        db.session.flush()
# #        #.products.delete().where(
# #        #    (products.c.tenant_id==g.tenant['tenant_id'])&
# #        #    (products.c.product_id==product_id)))
# #    except:
# #        pass
# #    return ({}, 200, [])
# #
