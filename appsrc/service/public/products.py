import simplejson as json
from urllib import parse

from sqlalchemy.orm import exc as orm_exc
from flask import current_app as app

from ...db import db
from ...db.models.products import Product, ProductSchema as PSchema
from ...db.models.groups import Group, GroupOption, ProductGroupOption
from ...utils.uuid import clean_uuid
from ..routes.routing import json_abort, hal, api_url
from ..products import _delocalize_product_field, _get_product_groups
from ..images import img_aspect_ratios

#from .validation.products import (add_product, edit_product)


def get_public_group(group_id, domain, lang):
    try:
        grp = Group.query.filter_by(
            group_id=group_id, domain_id=domain.domain_id).one()
    except:
        json_abort(404, {'error': 'Group not found'})

    return _get_group_resource(grp, lang), 200, []

def get_public_groups(domain, lang):
    domain_id = domain.domain_id
    groups = Group.query.filter_by(domain_id=domain_id, active=True).all()
    rv = hal()
    rv._l('self', api_url('api.get_public_groups'))
    rv._embed('groups',[
        _get_group_resource(grp, lang) for grp in  groups
    ])
    return rv.document, 200, []

def _getlabel(data, lang):
    try:
        return (data.get('label') or {}).get(lang) or ''
    except:
        return ''

def _get_group_resource(grp, lang):
    rv = hal()
    rv._l('self', api_url(
        'api.get_public_group', group_id=grp.group_id))
    rv._k('group_id', grp.group_id)
    rv._k('label', _getlabel(grp.data,lang))
    # TODO: GET actions should not mutate the data, move this to
    # POST and PUT.
    rv._k('multichoice', grp.data.setdefault('multichoice', True))
    rv._k('options',
          [{'group_option_id':fo.group_option_id,
            'label':_getlabel(fo.data, lang)
           } for fo in grp.options ])
    return rv.document

def get_public_products(params, domain):
    domain_id = domain.domain_id
    # create a base query object
    q = Product.query.filter(Product.domain_id==domain_id)
    # groups are passed as url quoted json string
    if params.get('groups'):
        # TODO: validate that this is a list of objects with format
        # {'options': [...]}
        groups = json.loads(parse.unquote(params['groups']))
        for grp in groups:
            subq = ProductGroupOption.filter(
                ProductGroupOption.group_id.in_(grp['options'])).subquery()
            q = q.join(subq, Product.product_id==subq.c.product_id)
        #subq = qrs[1].subquery()
        #q = qrs[0].join(subq, Product.product_id==subq.c.product_id)
    products = q.all()
    product_url = api_url('api.get_public_product', product_id='{product_id}')
    rv = hal()
    rv._l('self', api_url('api.get_public_products',**params))
    rv._l(f'{app.config.API_NAMESPACE}:product', product_url, unquote=True, templated=True)
    rv._k('products', [p.product_id for p in products])
    return rv.document, 200, []

def grouped_query(q, group_id):
    grp = Group.query.filter(Group.group_id==group_id).subquery()
    return q.join(grp, grp.c.group_id==Group.group_id)

def get_public_product_resources(params, domain, lang):
    product_ids = params.getlist('pid')
    q = Product.query.filter_by(domain_id=domain.domain_id)
    products = q.filter(Product.product_id.in_(product_ids)).all()
    rv = hal()
    rv._l('self', api_url('api.get_product_resources'))
    rv._k('product_ids', [p.product_id for p in products])
    rv._embed('products', [_get_product_resource(p, lang) for p in products])
    return rv.document, 200, []

def _get_product_resource(p):
    rv = hal()
    rv._l('self', api_url(
        'api.get_public_product', product_id=clean_uuid(p.product_id)))
    rv._k('product_id', clean_uuid(p.product_id))
    #rv._k('available', p.available)
    rv._k('fields', [f.get('en') for f in p.fields.setdefault('fields', [])])
    #rv._k('unit_price', p.fields.get('unit_price'))
    #rv._k('quantity_unit', p.fields.get('quantity_unit'))
    rv._k('groups', _get_product_group_options(p.group_options))
    return rv.document

def _get_product_resource(p, lang):
    rv = hal()
    rv._l('self', api_url('api.get_product', product_id=p.product_id))
    rv._l('images', api_url('api.get_product_images', product_id=p.product_id))
    rv._l('groups', api_url('api.put_product_groups', product_id=p.product_id))
    rv._k('product_id', clean_uuid(p.product_id))
    rv._k('groups', _get_product_groups(p))
    rv._k('priority', p.priority)
    rv._k('last_update', p.updated_ts)
    rv._k('images', [img_aspect_ratios(
        i.image, aspect_ratios=['1:1'], sizes=['thumb', 'medium'])
        for i in p.images ])
    rv._k('fields', [_delocalize_product_field(
        f, lang) for f in p.fields.setdefault('fields', [])])
    # NOTE: maybe we'll add this at some point
    #rv._k('unit_price', p.data.get('unit_price'))
    #rv._k('quantity_unit', p.data.get('quantity_unit'))
    return rv.document

def _get_product_group_options(group_options):
    groups = {}
    for o in group_options:
        fo = groups.setdefault(clean_uuid(o.group_id), [])
        fo.append(clean_uuid(o.group_option_id))
    return [{'group_id': k, 'options': v} for k,v in groups.items()]

def _get_product(product_id, domain_id):
    product_id = clean_uuid(product_id)
    try:
        if product_id is None:
            raise orm_exc.NoResultFound()
        return Product.query.filter_by(product_id=product_id,
                                       domain_id=domain_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error': 'Product Not Found'})

def get_public_product(product_id, domain, params):
    # in the meantime, while waiting for validation
    product = _get_product(product_id, domain.domain_id)
    document = _get_product_resource(product)
    return document, 200, []

#def grouped_query(q, groups):
#    group_path = 'data#>\'{{fields,{name},value}}\''
#    text_group = '{} @> \'"{{value}}"\''.format(group_path)
#    bool_group = '{} @> \'{{value}}\''.format(group_path)
#
#    for n,v in groups:
#        if v in (True,False):
#            v = str(v).lower()
#            q = q.filter(db.text(bool_group.format(name=n, value=v)))
#        else:
#            q = q.filter(db.text(text_group.format(name=n, value=v)))
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

def get_public_product_schema(domain):
    ps = _set_default_product_schema(domain.domain_id)
    rv = hal()
    rv._l('self', api_url('api.get_public_product_schema'))
    for k,v in ps.data.items():
        rv._k(k, v)
    return rv.document, 200, []
