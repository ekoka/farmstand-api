import simplejson as json
import copy

from .routes.routing import hal, api_url
from .utils import run_or_abort
from .images import _image_resource
from ..utils.uuid import clean_uuid
from ..db.schema import generic as product_schema

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

def _get_product_resource(product, lang):
    # api - resource
    rv = hal()
    pid = clean_uuid(product.product_id)
    rv._l('self', api_url(
        'api.get_product', product_id=pid))
    rv._l('images', api_url(
        'api.get_product_images', product_id=pid))
    rv._l('groups', api_url(
        'api.put_product_groups', product_id=pid))
    rv._k('product_id', pid)
    rv._k('groups', _get_product_groups_dict(product))
    rv._k('priority', product.priority)
    rv._k('last_update', product.updated_ts)
    rv._k('images', [
        _image_resource(img.image, aspect_ratios=['1:1'], sizes=['thumb', 'medium'])
        for img in product.images ])
    rv._k('fields', [_delocalize_product_field(f, lang)
                     for f in product.fields.setdefault('fields', [])])
    # NOTE: maybe we'll add this at some point.
    #rv._k('unit_price', product.data.get('unit_price'))
    #rv._k('quantity_unit', product.data.get('quantity_unit'))
    # TODO:
    #rv._embed('groups', [_get_group_resource(f, True) for f in product.groups])
    return rv.document

def _get_product_groups_dict(product):
    # api
    rv = {}
    for go in product.group_options:
        g_id = clean_uuid(go.group_id)
        go_id = clean_uuid(go.group_option_id)
        rv.setdefault(g_id, []).append(go_id)
    return rv

def _get_product_groups_list(group_options):
    # api
    groups = {}
    for o in group_options:
        # TODO: GET actions should not mutate the data, move this to POST and PUT.
        go = groups.setdefault(clean_uuid(o.group_id), [])
        go.append(clean_uuid(o.group_option_id))
    return [{'group_id': gid, 'options': opts} for gid,opts in groups.items()]

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
