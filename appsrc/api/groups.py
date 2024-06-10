from .product_utils import _delocalize_data
from .utils import run_or_abort
from .routes.routing import hal, api_url
from ..service import groups as grp_srv
from ..utils.uuid import clean_uuid

def get_groups(lang, domain):
    fnc = lambda: grp_srv.get_groups(domain.domain_id)
    groups = run_or_abort(fnc)
    rv = hal()
    rv._l('self', api_url('api.get_groups'))
    rv._l(f'{app.config.API_NAMESPACE}:group', api_url(
        'api.get_group', group_id='{group_id}'), templated=True, unquote=True)
    rv._l(f'{app.config.API_NAMESPACE}:group_resources', api_url('api.get_group_resources'))
    rv._k('group_ids', [grp.group_id for grp in groups])
    return rv.document, 200, []

def get_group_resources(params, domain, lang):
    # api
    group_ids = params.getlist('fid')
    domain_id = domain.domain_id
    fnc = lambda: grp_srv.get_group_resources(domain_id, group_ids)
    groups = run_or_abort(fnc)
    rv = hal()
    rv._l('self', api_url('api.get_group_resources'))
    rv._k('group_ids', [grp.group_id for grp in groups])
    rv._embed('groups', [_group_resource(grp, lang) for grp in groups])
    return rv.document, 200, []

# TODO: review
def post_group(data, lang, domain):
    # api
    fnc = lambda: grp_srv.create_group(domain.domain_id, data, lang)
    group = run_or_abort(fnc)
    rv = hal()
    location = api_url('api.get_group', group_id=group.group_id)
    rv._l('location', location)
    rv._k('group_id', group.group_id)
    return rv.document, 201, [('Location', location)]

def put_group(group_id, data, lang, domain):
    # api
    fnc = lambda: grp_srv.update_group(group_id, domain_id, data, lang)
    run_or_abort(fnc)
    return {}, 200, []

def _group_resource(grp, lang,):
    # api - resource
    rv = hal()
    rv._l('self', api_url('api.get_group', group_id=grp.group_id))
    rv._l('options', api_url('api.post_group_option', group_id=grp.group_id))
    rv._l('option', api_url(
        'api.get_group_option', group_id=grp.group_id, group_option_id='{group_option_id}'),
          templated=True, unquote=True)
    rv._k('group_id', grp.group_id)
    rv._k('active', grp.active)
    rv._k('multichoice', grp.multichoice)
    rv._k('data', _delocalize_data(grp.data, ['label', 'description'], lang))
    rv._k('options', [{
        'data': _delocalize_data(o.data, ['label'], lang),
        'group_option_id': clean_uuid(o.group_option_id)} for o in grp.options])
    return rv.document

def get_group(group_id, lang, domain):
    # api
    fnc = lambda: grp_srv.get_group(group_id, domain.domain_id)
    grp = run_or_abort(fnc)
    rv = _group_resource(grp, lang)
    return rv, 200, []

def delete_group(group_id, domain):
    # api
    fnc = lambda: grp_srv.delete_group(group_id, domain.domain_id)
    run_or_abort(fnc)
    return {}, 200, []

def _group_option_resource(group_option, lang):
    # api - resource
    g_o = group_option
    rv = hal()
    rv._l('self', api_url('api.get_group_option', group_id=g_o.group_id,
                          group_option_id=g_o.group_option_id))
    rv._l('products', api_url(
        'api.put_group_option_products', group_id=g_o.group_id,
        group_option_id=g_o.group_option_id))
    #if not partial:
    #    rv._l('group', api_url('api.get_group', group_id=g_o.group_id))
    rv._k('group_option_id', g_o.group_option_id)
    rv._k('data', _delocalize_data(g_o.data, ['label'], lang))
    rv._k('products', [p.product_id for p in group_option.products])
    return rv.document

def post_group_option(group_id, data, lang, domain):
    # api
    fnc = lambda: grp_srv.create_group_option(group_id, domain.domain_id, data, lang)
    g_o = run_or_abort(fnc)
    rv = hal()
    location = api_url(
        'api.get_group_option', group_id=group_id, group_option_id=g_o.group_option_id)
    rv._l('location', location)

def get_group_option(group_id, group_option_id, lang, domain):
    fnc = lambda: grp_srv.get_group_option(group_id, group_option_id, domain.domain_id)
    g_o = run_or_abort(fnc)
    rv = _group_option_resource(g_o, lang)
    return rv, 200, []

def put_group_option(group_id, group_option_id, data, lang, domain):
    # api
    fnc = lambda: grp_srv.update_group_option(
        group_id, group_option_id, domain.domain_id, data, lang)
    run_or_abort(fnc)
    return {}, 200, []

def delete_group_option(group_id, group_option_id, domain):
    # api
    domain_id = domain.domain_id
    fnc = lambda: grp_srv.delete_group_option(group_id, group_option_id, domain_id)
    run_or_abort(fnc)
    return {}, 200, []

def put_group_option_products(group_id, group_option_id, domain, data):
    # api
    fnc = lambda: grp_srv.update_group_option_products(
        group_id, group_option_id, domain.domain_id, data)
    run_or_abort(fnc)
    return {}, 200, []
