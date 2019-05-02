from flask import url_for, current_app as app

from b2bapi.db.models.domains import Domain
from .._route import route, hal, json_abort, api_url
from ..utils import delocalize_data
    
#@route('/<path:catchall>')
#def catchall(*a, **kw):
#    abort(404)

@route('/public/root', expects_domain=True, expects_lang=True)
def get_public_root(domain, lang):
    rv = hal()
    rv._l('self', api_url('api.get_public_root'))
    rv._l('productlist:public_domain', api_url('api.get_public_domain', 
        domain_name="{domain}"), unquote=True, templated=True)
    rv._l('productlist:public_products', api_url(
        'api.get_public_products', domain=domain.name))
    rv._l('productlist:public_groups', api_url(
        'api.get_public_groups', domain=domain.name))
    rv._l('productlist:public_product_schema', api_url(
        'api.get_public_product_schema', domain=domain.name))
    rv._l('productlist:public_product_resources', api_url(
        'api.get_public_product_resources', domain=domain.name))
    #TODO: later when implementing inquiries
    #rv._l('simpleb2b:public-inquiries', api_url('api.post_public_inquiry'))
    rv._l('productlist:public_product', api_url(
        'api.get_public_product', product_id="{product_id}",
        domain=domain.name), unquote=True, templated=True)
        #'/api/v1/domain-name-search?name={domain}', templated=True)
    rv._l('productlist:domain_host_template', app.config[
        'SUBDOMAIN_HOST_TEMPLATE'], templated=True, unquote=True)
    rv._l('productlist:api_host', app.config['API_HOST'])
    rv._l('productlist:account_host', app.config['ACCOUNT_HOST'])

    rv._k('catalog', _get_catalog_information(domain, lang))

    return rv.document, 200, []


def _get_catalog_information(domain, lang):
    from flask import current_app as app
    data = delocalize_data(domain.data, Domain.localized_fields, lang)
    rv = {
        'domain': domain.name,
        'label': data.get('label') or domain.name,
        'description': data.get('description', None) 
    }
    return rv

