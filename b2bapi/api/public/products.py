import simplejson as json

from flask import redirect, g, current_app as app, abort, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db import db
from b2bapi.db.models.products import Product, ProductSchema as PSchema
from b2bapi.db.models.filters import Filter, FilterSet as FSet
from b2bapi.utils.uuid import clean_uuid
from .._route import route, json_abort, hal

#from .validation.products import (add_product, edit_product)


# ------------------------ Products ------------------------ # 
def _get_filter_resource(f, partial=False):
    rv = hal()
    rv._l('self', url_for('api.get_public_filter', filter_id=f.filter_id))
    rv._k('filter_id', f.filter_id)
    rv._k('label', f.data.setdefault('label',{'en':None}).get('en'))
    if f.parent and not partial:
        rv._embed('parent', _get_filter_resource(f.parent, partial=True))
        rv._k('level', f.level)
    return rv.document

@route('/public/filters/<filter_id>', expects_tenant=True)
def get_public_filter(filter_id, tenant):
    try:
        f = Filter.query.filter_by(
            filter_id=filter_id, tenant_id=tenant.tenant_id).one()
    except:
        json_abort(404, {'error': 'Filter not found'})

    return _get_filter_resource(f), 200, []

@route('/public/filter-sets', expects_tenant=True)
def get_public_filter_sets(tenant):
    tenant_id = tenant.tenant_id
    fsets = FSet.query.filter_by(tenant_id=tenant_id).all()

    rv = hal() 
    rv._l('self', url_for('api.get_public_filter_sets'))
    rv._embed('filter_sets',[
        _get_filter_set_resource(fs) for fs in  fsets
    ])

    return rv.document, 200, []

@route('/public/filter-sets/<filter_set_id>', expects_tenant=True)
def get_public_filter_set(filter_set_id, tenant):
    pass

def _get_filter_set_resource(fs):
    app.logger.info(fs.filters)
    rv = hal()
    rv._l('self', url_for(
        'api.get_public_filter_set', filter_set_id=fs.filter_set_id))
    rv._k('filter_set_id', fs.filter_set_id)
    rv._k('label', fs.data.setdefault('label', {'en':None}).get('en'))
    rv._k('multichoice', fs.data.setdefault('multichoice', True))
    rv._k('filters', 
          [{'filter_id':f.filter_id, 'label':f.data.setdefault(
              'label', {'en':None}).get('en')}
           for f in fs.filters ])
    return rv.document

@route('/public/products', expects_params=True, expects_tenant=True)
def get_public_products(params, tenant):
    tenant_id = tenant.tenant_id
    baseq = Product.query.filter(Product.tenant_id==tenant_id)
    
    if params.get('filters'):
        filters = params.getlist('filters')
        subqrs = []
        for set_id in params.getlist('sets'):
            subq = (Product.query.join(Product.filters).filter(Filter.filter_id.in_(filters), 
                            Filter.filter_set_id==set_id).subquery())
            baseq = baseq.join(subq, Product.product_id==subq.c.product_id)

        #subq = qrs[1].subquery()
        #q = qrs[0].join(subq, Product.product_id==subq.c.product_id)
        
    products = baseq.all()

    product_url = url_for('api.get_public_product', product_id='{product_id}')
    rv = hal()
    rv._l('self', url_for('api.get_public_products',**params))
    #rv._l('simpleb2b:product', product_url, unquote=True, templated=True)

    rv._embed('products', [_get_product_resource(p, partial=True)
                           for p in products])
    return rv.document, 200, []

def filtered_query(q, set_id):
    fs = FSet.query.filter(FSet.filter_set_id==set_id).subquery()
    return q.join(fs, fs.c.filter_set_id==Filter.filter_set_id)
    

#def query():
#    return text('''
#    SELECT p.* FROM products p
#    INNER JOIN  products_filters pf
#    ON pf.product_id = p.product_id
#    INNER JOIN filters f
#    ON f.filter_id=pf.filter_id
#    INNER JOIN (
#        SELECT filter_set_id 
#        FROM filter_sets OFFSET {offset} LIMIT 1
#    fs
#    ON fs.filter_set_id = f.filter_set_id
#    WHERE  f.filter_id in :filter_ids
#                ''', {filter_ids:[]})

def _get_product_resource(p, partial=True):
    rv = hal()
    rv._l('self', url_for('api.get_public_product', product_id=p.product_id,
                          partial=partial))
    rv._k('product_id', p.product_id.hex)
    if partial:
        rv._k('partial', partial)
        rv._k('fields', [f.get('en') 
                         for f in p.data.setdefault('fields', [])[:3]])
    else:
        rv._k('available', p.available)
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

@route('/public/products/<product_id>', authenticate=True, expects_tenant=True,
       expects_params=True)
def get_public_product(product_id, tenant, params):
    # in the meantime, while waiting for validation
    partial = int(params.get('partial', False))
    app.logger.info(partial)
    product = _get_product(product_id, tenant.tenant_id)
    document = _get_product_resource(product, partial=partial)
    return document, 200, []

#def filtered_query(q, filters):
#    filter_path = 'data#>\'{{fields,{name},value}}\''
#    text_filter = '{} @> \'"{{value}}"\''.format(filter_path)
#    bool_filter = '{} @> \'{{value}}\''.format(filter_path)
#
#    for n,v in filters:
#        if v in (True,False):
#            v = str(v).lower()
#            q = q.filter(db.text(bool_filter.format(name=n, value=v)))
#        else:
#            q = q.filter(db.text(text_filter.format(name=n, value=v)))
#    return q

# ---------------------------------------------------------------- # 
# ---------------------------------------------------------------- # 

# ------------------------ Product Schema ------------------------ # 

def _set_default_product_schema(tenant_id):
    ps = PSchema.query.get(tenant_id)
    if not ps:
        try:
            ps = PSchema(product_schema_id=tenant_id)
            db.session.add(ps)
            db.session.flush()
        except Exception as e:
            db.session.rollback()
            json_abort(401, {})
    return ps

@route('/public/product-schema', expects_tenant=True)
def get_public_product_schema(tenant):
    ps = _set_default_product_schema(tenant.tenant_id)
    rv = hal()
    rv._l('self', url_for('api.get_public_product_schema'))
    for k,v in ps.data.items():
        rv._k(k, v)
    return rv.document, 200, []
