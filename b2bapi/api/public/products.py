import simplejson as json

from flask import redirect, g, current_app as app, abort, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db import db
from b2bapi.db.models.products import Product, ProductSchema as PSchema
from b2bapi.db.models.filters import Filter, FilterOption
from b2bapi.utils.uuid import clean_uuid
from .._route import route, json_abort, hal

#from .validation.products import (add_product, edit_product)


# ------------------------ Products ------------------------ # 
def _get_filter_resource(f):
    rv = hal()
    rv._l('self', url_for('api.get_public_filter', filter_id=clean_uuid(f.filter_id)))
    rv._k('filter_id', clean_uuid(f.filter_id))
    return rv.document

@route('/public/filters/<filter_id>', expects_domain=True)
def get_public_filter(filter_id, domain):
    try:
        f = Filter.query.filter_by(
            filter_id=filter_id, domain_id=domain.domain_id).one()
    except:
        json_abort(404, {'error': 'Filter not found'})

    return _get_filter_resource(f), 200, []

@route('/public/filters', expects_domain=True)
def get_public_filters(domain):
    domain_id = domain.domain_id
    filters = Filter.query.filter_by(domain_id=domain_id).all()

    rv = hal() 
    rv._l('self', url_for('api.get_public_filters'))
    rv._embed('filters',[
        _get_filter_resource(s) for f in  filters 
    ])

    return rv.document, 200, []

@route('/public/filters/<filter_id>', expects_domain=True)
def get_public_filter(filter_id, domain):
    pass

def _get_filter_resource(f):
    rv = hal()
    rv._l('self', url_for(
        'api.get_public_filter', filter_id=f.filter_id))
    rv._k('filter_id', f.filter_id)
    rv._k('label', f.data.setdefault('label', {'en':None}).get('en'))
    rv._k('multichoice', f.data.setdefault('multichoice', True))
    rv._k('options', 
          [{'filter_option_id':fo.filter_option_id, 'label':fo.data.setdefault(
              'label', {'en':None}).get('en')}
           for fo in f.options ])
    return rv.document

@route('/public/products', expects_params=True, expects_domain=True)
def get_public_products(params, domain):
    domain_id = domain.domain_id
    q = Product.query.filter(Product.domain_id==domain_id)
    
    # params is a quoted json
    try:
        data = json.loads(parse.unquote(params))
    except:
        json_abort(400, {'error': 'Invalid token'})
    if params.get('filters'):
        options = params.getlist('options')
        subqrs = []
        for filter_id in params.getlist('filters'):
            subq = (Product.query.join(Product.filters).filter(
                Filter.filter_id.in_(filters), 
                Filter.filter_id==filter_id).subquery())
            q = q.join(subq, Product.product_id==subq.c.product_id)

        #subq = qrs[1].subquery()
        #q = qrs[0].join(subq, Product.product_id==subq.c.product_id)
        
    products = q.all()

    product_url = url_for('api.get_public_product', product_id='{product_id}')
    rv = hal()
    rv._l('self', url_for('api.get_public_products',**params))
    rv._l('simpleb2b:product', product_url, unquote=True, templated=True)
    rv._k('products', [p.product_id for p in products])
    return rv.document, 200, []

def filtered_query(q, filter_id):
    f = Filter.query.filter(Filter.filter_id==filter_id).subquery()
    return q.join(f, f.c.filter_id==Filter.filter_id)
    
def _get_product_resource(p):
    rv = hal()
    rv._l('self', url_for(
        'api.get_public_product', product_id=clean_uuid(p.product_id)))
    rv._k('product_id', clean_uuid(p.product_id))
    #rv._k('available', p.available)
    rv._k('fields', [f.get('en') for f in p.fields.setdefault('fields', [])])
    #rv._k('unit_price', p.fields.get('unit_price'))
    #rv._k('quantity_unit', p.fields.get('quantity_unit'))
    rv._k('filters', _get_product_filter_options(p.filter_options))
    return rv.document

def _get_product_filter_options(filter_options):
    filters = {}
    for o in filter_options:
        fo = filters.setdefault(clean_uuid(o.filter_id), [])
        fo.append(clean_uuid(o.filter_option_id))
    return [{'filter_id': k, 'options': v} for k,v in filters.items()]

def _get_product(product_id, domain_id):
    product_id = clean_uuid(product_id)
    try:
        if product_id is None:
            raise orm_exc.NoResultFound()
        return Product.query.filter_by(product_id=product_id, 
                                       domain_id=domain_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error': 'Product Not Found'})

@route('/public/products/<product_id>', authenticate=True, expects_domain=True,
       expects_params=True)
def get_public_product(product_id, domain, params):
    # in the meantime, while waiting for validation
    product = _get_product(product_id, domain.domain_id)
    document = _get_product_resource(product)
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

def _set_default_product_schema(domain_id):
    ps = PSchema.query.filter_by(domain_id=domain_id).first()
    if not ps:
        try:
            ps = PSchema(domain_id=domain_id)
            db.session.add(ps)
            db.session.flush()
        except Exception as e:
            db.session.rollback()
            json_abort(401, {})
    return ps

@route('/public/product-schema', expects_domain=True)
def get_public_product_schema(domain):
    ps = _set_default_product_schema(domain.domain_id)
    rv = hal()
    rv._l('self', url_for('api.get_public_product_schema'))
    for k,v in ps.data.items():
        rv._k(k, v)
    return rv.document, 200, []
