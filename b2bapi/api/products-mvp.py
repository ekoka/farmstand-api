import uuid
import simplejson as json

from flask import redirect, g, current_app as app, abort, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db import db
from b2bapi.db.models.products import Product, ProductSchema as PSchema
from b2bapi.db.models.filters import Filter
from b2bapi.utils.uuid import clean_uuid
from ._route import route, json_abort, hal

from .validation.products import (add_product, edit_product)
from .filters import _get_filter_resource


# ------------------------ Products ------------------------ # 

@route('/products', methods=['GET'], expects_params=True, expects_tenant=True,
       authenticate=True)
def get_products(params, tenant):
    tenant_id = tenant.tenant_id
    q = Product.query.filter_by(tenant_id=tenant_id)
    #if params.get('filters'): 
    #    filters = json.loads(params['filters'])
    #    q = filtered_query(q, [(k,v) for k,v in filters.iteritems()])
    products = q.all()
    product_url = url_for('api.get_product', product_id='{product_id}')
    rv = hal()
    rv._l('self', url_for('api.get_products',**params))
    rv._l('simpleb2b:product', product_url, unquote=True, templated=True)

    rv._embed('products', [_get_product_resource(p, partial=True)
                           for p in products])
    return rv.document, 200, []

def _get_product_resource(p, partial=True):
    rv = hal()
    rv._l('self', url_for('api.get_product', product_id=p.product_id,
                          partial=partial))
    rv._k('product_id', p.product_id.hex)
    if partial:
        rv._k('partial', partial)
        rv._k('fields', [f.get('en') 
                         for f in p.data.setdefault('fields', [])[:3]])
    else:
        rv._k('available', p.available)
        rv._k('visible', p.visible)
        rv._k('fields', [f.get('en') for f in p.data.setdefault('fields', [])])
        rv._k('unit_price', p.data.get('unit_price'))
        rv._k('quantity_unit', p.data.get('quantity_unit'))
        rv._embed('filters', [_get_filter_resource(f, True) for f in p.filters])
    return rv.document

def _get_product(product_id, tenant_id):
    product_id = clean_uuid(product_id)
    try:
        if product_id is None:
            raise orm_exc.NoResultFound()
        return Product.query.filter_by(product_id=product_id, 
                                       tenant_id=tenant_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error': 'Product Not Found'})

@route('/products/<product_id>', authenticate=True, expects_tenant=True,
       expects_params=True)
def get_product(product_id, tenant, params):
    # in the meantime, while waiting for validation
    partial = int(params.get('partial', False))
    product = _get_product(product_id, tenant.tenant_id)
    document = _get_product_resource(product, partial=partial)
    return document, 200, []


def populate_product(product, data):
    for k,v in data.items():
        if k=='data':
            for kk, vv in v.items():
                if kk=='fields':
                    _merge_fields(product.data, vv)
                else:
                    product.data[kk] = vv
            #product.data = {k: v}
        else:
            setattr(product,k,v)

def _merge_fields(productdata, datafields):
    field_types = {f.name: f.field_type for f in Field.query.all()}
    for df in datafields:
        field_type = field_types.get(df.get('name'))
        if field_type in Field.text_types:
            df['value'], value = {}, df.get('value') # uploaded value
            #if product.data and product.data.fields:
            for pf in productdata['fields']:
                if pf.get('name')==df['name']:
                    df['value'] = pf.get('value', {}) # localized values
            df['value']= value # merge localized and uploaded value 
    productdata['fields'] = datafields


def db_flush():
    try:
        db.session.flush()
    except sql_exc.IntegrityError as e:
        raise
        db.session.rollback()
        json_abort(400, {'error': 'Could not save record. Verify format.'})

@route('/products', methods=['POST'], expects_data=True, authenticate=True,
       expects_tenant=True)
def post_product(data, tenant):
    # TODO validation
    #try:
    #    data = add_product.validate(data)
    #except vno_err.ValidationErrorStack as e:
    #    abort(400, 'Invalid data ' + str(e))

    # while we're waiting for proper validation
    filters = data.pop('filters', [])

    data['data'] = {
        'quantity_unit' : data.pop('quantity_unit', None),
        'unit_price' : data.pop('unit_price', None),
        'fields' : [{'en': f} for f in data.pop('fields', [])],
    }
    data['tenant_id'] = tenant.tenant_id

    p = Product(**data)

    for f in filters:
        p.product_filters.append(ProductFilter(filter_id=f.filter_id))
    db.session.add(p)
    db_flush()
    location = url_for('api.get_product', product_id=p.product_id, partial=False)
    rv = hal()
    rv._l('location', location)
    rv._k('product_id', p.product_id)
    return rv.document, 201, [('Location', location)]

@route('/products/<product_id>', methods=['PUT'], expects_data=True,
       authenticate=True, expects_tenant=True)
def put_product(product_id, data, tenant):
    # TODO: validation
    # data = edit_product.validate(data)
    p = _get_product(product_id, tenant.tenant_id)

    filters = data.pop('filters', [])
    fields = data.pop('fields', [])
    data.pop('data', None)
    p.populate(**data)

    try:
        for i,f in enumerate(fields):
            try:
                val = p.data.setdefault('fields', [])[i]
                val['en'] = f
            except IndexError:
                val = {'en': f}
                p.data.setdefault('fields', []).append(val)
    except:
        json_abort(400, {'error':'Bad Format'})

    p.filters = Filter.query.filter(Filter.filter_id.in_(filters)).all()

    db_flush()
    return {}, 200, []

@route('/products/<product_id>', methods=['DELETE'], authenticate=True,
       expects_tenant=True)
def delete_product(product_id, tenant):
    try:
        p = _get_product(product_id, tenant.tenant_id)
        db.session.delete(p)
        db.session.flush()
        #.products.delete().where(
        #    (products.c.tenant_id==g.tenant['tenant_id'])&
        #    (products.c.product_id==product_id)))
    except:
        pass
    return {}, 200, []


def filtered_query(q, filters):
    filter_path = 'data#>\'{{fields,{name},value}}\''
    text_filter = '{} @> \'"{{value}}"\''.format(filter_path)
    bool_filter = '{} @> \'{{value}}\''.format(filter_path)

    for n,v in filters:
        if v in (True,False):
            v = str(v).lower()
            q = q.filter(db.text(bool_filter.format(name=n, value=v)))
        else:
            q = q.filter(db.text(text_filter.format(name=n, value=v)))
    return q

# ---------------------------------------------------------------- # 
# ---------------------------------------------------------------- # 

# ------------------------ Product Schema ------------------------ # 

def _set_default_product_schema(tenant_id):
    ps = PSchema.query.get(tenant_id)
    if ps:
        return ps
    try:
        ps = PSchema(product_schema_id=tenant_id)

        ps.data['fields'] =  [None for i in range(5)]
        db.session.add(ps)
        db.session.flush()
        return ps
    except Exception as e:
        db.session.rollback()
        json_abort(401, {})

@route('/product-schema', authenticate=True, expects_tenant=True)
def get_product_schema(tenant):
    ps = _set_default_product_schema(tenant.tenant_id)
    rv = hal()
    rv._l('self', url_for('api.get_product_schema'))

    #for k,v in ps.data.items():

    def getitem(l, i, default=None):
        try:
            return l[i]
        except:
            l.append(default)
            return default

    rv._k('fields', ps.data['fields'])
    return rv.document, 200, []
   
@route('/product-schema', methods=['PUT'], authenticate=True, 
       expects_tenant=True, expects_data=True)
def put_product_schema(data, tenant):
    ps = _set_default_product_schema(tenant.tenant_id)
    for k,v in data.items():
        ps.data[k] = v
    db.session.flush()
    rv = hal()
    rv._l('product_schema', url_for('api.get_product_schema'))
    return rv.document, 200, []

