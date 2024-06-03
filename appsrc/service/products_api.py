import simplejson as json
import copy

from ..utils.uuid import clean_uuid
from ..db.schema import generic as product_schema
from .routes.routing import hal, api_url
from .images import img_aspect_ratios
from .utils import run_or_abort

def _delocalize_product_field(field, lang):
    """
    delocalize fields, i.e. remove the lang context from field
    """
    rv = dict(**field)
    if field.get('localized'):
        try:
            rv['value'] = rv.setdefault('value', {}).get(lang)
        except AttributeError:
            pass
        rv['localized'] = True
    return rv


def _localized_field_schema(field, lang):
    rv = {}
    rv['label'] = field['schema']['label'][lang]
    if field['field_type']=='BOOL':
        for v in (True, False):
            rv.setdefault('options',{})[v] = field['schema']['options'][v][lang]
        return rv
    if field['field_type'] in ('MULTI_CHOICE', 'SINGLE_CHOICE',):
        for o in field['schema']['options']:
            rv.setdefault('options',[]).append(
                {'value': o['value'], 'label': o['label'][lang]})
    return rv

def _field_schema(f, lang):
    field = copy.deepcopy(f['field'])
    field['display'] = f.get('display', False)
    field['searchable'] = f.get('searchable', False)
    field['localized'] = f.get('localized', False)
    field['schema'] = _localized_field_schema(field, lang)
    return field

def get_products(params, domain, lang):
    # api
    last_product_id = params.get('last_product')
    search_query = params.get('q')
    fnc = lambda: prod_srv.get_products(domain, lang, last_product_id, search_query)
    result = run_or_abort(fnc)
    rv = hal()
    product_url = api_url('api.get_product', product_id='{product_id}')
    rv._l('self', api_url('api.get_products', **params))
    rv._l(f'{app.config.API_NAMESPACE}:product', product_url, unquote=True, templated=True)
    rv._k('product_ids', result['product_ids'])
    rv._k('last_product', result['last_product'])
    rv._k('has_more', result['has_more'])
    return rv.document, 200, []

def get_product_resources(params, domain, lang):
    # api
    product_ids = params.getlist('pid')
    domain_id = domain.domain_id
    fnc = lambda: prod_srv.get_product_by_ids(product_ids, domain_id, lang)
    products = run_or_abort(fnc)
    rv = hal()
    rv._l('self', api_url('api.get_product_resources'))
    rv._k('product_ids', [p.product_id for p in products])
    rv._embed('products', [_get_product_resource(p, lang) for p in products])
    return rv.document, 200, []

def get_product_schema(lang):
    # api
    rv = hal()
    rv._l('self', api_url('api.get_product_schema'))
    rv._k('name', product_schema['name'])
    rv._k('fields', [_field_schema(f, lang) for f in product_schema['schema']['fields']])
    return rv.document, 200, []

def get_product_json(product_id, domain):
    # api
    fnc = lambda: prod_srv.get_product(product_id, domain.domain_id)
    product = run_or_abort(fnc)
    data = json.dumps(product.fields, indent=4)
    return {'json':data}, 200, []

def put_product_json(product_id, domain, data):
    # api
    fnc = lambda: prod_srv.set_product_fields(product_id, domain.domain_id, data)
    run_or_abort(fnc)
    return {}, 200, []

def get_product(product_id, domain, params, lang):
    # api
    # in the meantime, while waiting for validation
    partial = int(params.get('partial', False))
    fnc = lambda: prod_srv.get_product(product_id, domain.domain_id)
    product = run_or_abort(fnc)
    document = _get_product_resource(product, lang)
    return document, 200, []

def _get_product_resource(p, lang):
    # api - resource
    rv = hal()
    rv._l('self', api_url(
        'api.get_product', product_id=clean_uuid(p.product_id)))
    rv._l('images', api_url(
        'api.get_product_images', product_id=clean_uuid(p.product_id)))
    rv._l('groups', api_url(
        'api.put_product_groups', product_id=clean_uuid(p.product_id)))
    rv._k('product_id', clean_uuid(p.product_id))
    rv._k('groups', prod_srv.get_product_groups(p))
    rv._k('priority', p.priority)
    rv._k('last_update', p.updated_ts)
    rv._k('images', [img_aspect_ratios(
        i.image, aspect_ratios=['1:1'], sizes=['thumb', 'medium'])
        for i in p.images ])
    rv._k('fields', [_delocalize_product_field(f, lang)
                     for f in p.fields.setdefault('fields', [])])
    # NOTE: maybe we'll add this at some point.
    #rv._k('unit_price', p.data.get('unit_price'))
    #rv._k('quantity_unit', p.data.get('quantity_unit'))
    # TODO:
    #rv._embed('groups', [_get_group_resource(f, True) for f in p.groups])
    return rv.document

def post_product(data, lang):
    # api
    fnc = lambda: prod_srv.create_product(data, lang)
    p = run_or_abort(fnc)
    rv = hal()
    location = api_url('api.get_product', product_id=p.product_id, partial=False)
    rv._l('location', location)
    rv._k('product_id', p.product_id)
    return rv.document, 201, [('Location', location)]

def put_product(product_id, data, domain, lang):
    # api
    domain_id = domain.domain_id
    update_product = lambda: prod_srv.update_product(product_id, data, domain_id, lang)
    product = run_or_abort(update_product)
    update_search_index = lambda: prod_srv.update_search_index(product, lang)
    run_or_abort(update_search_index)
    return {}, 200, []

def put_product_groups(product_id, data, domain):
    # api
    groups = data.get('groups') or  []
    domain_id = domain.domain_id
    fnc = lambda: prod_srv.update_product_groups(product_id, groups, domain_id)
    run_or_abort(fnc)
    return {}, 200, []

def get_product_details(domain, lang, params):
    # api
    fnc = lambda: prod_srv.product_details(domain, params)
    products = run_or_abort(fnc)
    #TODO: validate params
    rv = hal()
    rv._l('self', api_url('api.get_product_details'))
    rv._embed('products', [_get_product_resource(p, lang) for p in products])
    return rv.document, 200, []

def patch_product(product_id, data, domain, lang):
    """
    For a data to be patched to the product, it must already be present.
    """
    # api
    domain_id = domain.domain_id
    fnc = lambda: prod_srv.patch_product(product_id, domain_id, data, lang)
    run_or_abort(fnc)
    return {}, 200, []

def delete_product(product_id):
    # api
    fnc = lambda: prod_srv.delete_product(product_id)
    run_or_abort(fnc)
    return ({}, 200, [])
