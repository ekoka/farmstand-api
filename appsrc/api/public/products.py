import simplejson as json
from urllib import parse
from flask import current_app as app

from ..routes.routing import hal, api_url
from ..utils import run_or_abort
from ..products import (
    _delocalize_product_field,
    _get_product_groups_dict,
    _get_product_groups_list)
from ..images import _image_resource
from ...service import groups as grp_srv, products as prd_srv
from ...utils.uuid import clean_uuid

#from .validation.products import (add_product, edit_product)

def get_public_group(group_id, domain, lang):
    # api
    fnc = lambda: grp_srv.get_group(group_id, domain.domain_id, active=True)
    group = run_or_abort(fnc)
    return _get_group_resource(group, lang), 200, []

def get_public_groups(domain, lang):
    # api
    domain_id = domain.domain_id
    groups = run_or_abort(lambda: grp_srv.get_groups(domain_id, active=True))
    rv = hal()
    rv._l('self', api_url('api.get_public_groups'))
    rv._embed('groups',[_get_group_resource(grp, lang) for grp in  groups])
    return rv.document, 200, []

def _get_group_resource(group, lang):
    # api
    def _label(data, lang):
        label_dict = data.get('label') or {}
        try:
            return label_dict.get(lang) or ''
        except:
            return ''
    rv = hal()
    rv._l('self', api_url('api.get_public_group', group_id=group.group_id))
    rv._k('group_id', group.group_id)
    rv._k('label', _label(group.data,lang))
    # TODO: GET actions should not mutate the data, move this to POST and PUT.
    rv._k('multichoice', group.data.setdefault('multichoice', True))
    option_dict = lambda opt: {
        'group_option_id': opt.group_option_id,
        'label':_label(opt.data, lang), }
    rv._k('options', [option_dict(opt) for opt in group.options])
    return rv.document

def get_public_products(domain, params):
    # api
    domain_id = domain.domain_id
    # groups are passed as url quoted json string
    # TODO: validate that this is a list of objects with format
    # {'options': [...]}
    groups = json.loads(parse.unquote(params['groups'])) if params.get('groups') else None
    fnc = lambda: prd_srv.get_products_filtered_by_group(domain_id, groups)
    products = run_or_abort(fnc)
    product_url = api_url('api.get_public_product', product_id='{product_id}')
    rv = hal()
    rv._l('self', api_url('api.get_public_products', **params))
    rv._l(f'{app.config.API_NAMESPACE}:product', product_url, unquote=True,
          templated=True)
    rv._k('products', [p.product_id for p in products])
    return rv.document, 200, []

def get_public_product_resources(params, domain, lang):
    # api
    product_ids = params.getlist('pid')
    domain_id = domain.domain_id
    fnc = lambda: prd_srv.get_product_by_ids(product_ids, domain_id, lang)
    products = run_or_abort(fnc)
    rv = hal()
    rv._l('self', api_url('api.get_product_resources'))
    rv._k('product_ids', [p.product_id for p in products])
    rv._embed('products', [_get_product_resource(p, lang) for p in products])
    return rv.document, 200, []

#def _get_product_resource(product):
#    # api
#    product_id = clean_uuid(product.product_id)
#    rv = hal()
#    rv._l('self', api_url('api.get_public_product', product_id=product_id))
#    rv._k('product_id', product_id)
#    #rv._k('available', p.available)
#    # TODO: GET actions should not mutate the data, move this to POST and PUT.
#    # TODO: Hardcoding lang here for now.
#    rv._k('fields', [f.get('en') for f in product.fields.setdefault('fields', [])])
#    #rv._k('unit_price', p.fields.get('unit_price'))
#    #rv._k('quantity_unit', p.fields.get('quantity_unit'))
#    rv._k('groups', _get_product_groups_list(product.group_options))
#    return rv.document

def _get_product_resource(product, lang):
    # api
    pid = clean_uuid(product.product_id)
    rv = hal()
    rv._l('self', api_url('api.get_product', product_id=pid))
    rv._l('images', api_url('api.get_product_images', product_id=pid))
    rv._l('groups', api_url('api.put_product_groups', product_id=pid))
    rv._k('product_id', pid)
    rv._k('groups', _get_product_groups_dict(product))
    rv._k('priority', product.priority)
    rv._k('last_update', product.updated_ts)
    rv._k('images', [_image_resource(
        img.image, aspect_ratios=['1:1'], sizes=['thumb', 'medium'])
        for img in product.images ])
    # TODO: GET actions should not mutate the data, move this to POST and PUT.
    rv._k('fields', [_delocalize_product_field(f, lang)
                     for f in product.fields.setdefault('fields', [])])
    # NOTE: maybe we'll add this at some point
    #rv._k('unit_price', product.data.get('unit_price'))
    #rv._k('quantity_unit', product.data.get('quantity_unit'))
    return rv.document

def get_public_product(product_id, domain, params, lang):
    # api
    # in the meantime, while waiting for validation
    product = run_or_abort(lambda: prd_srv.get_product(product_id, domain.domain_id))
    document = _get_product_resource(product, lang)
    return document, 200, []

# ------------------------ Product Schema ------------------------ #

def get_public_product_schema(domain):
    # api
    ps = run_or_abort(lambda: prd_srv.set_default_product_schema(domain.domain_id))
    rv = hal()
    rv._l('self', api_url('api.get_public_product_schema'))
    for k,v in ps.data.items():
        rv._k(k, v)
    return rv.document, 200, []
