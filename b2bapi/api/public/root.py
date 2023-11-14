from flask import current_app as app

from ...db.models.domains import Domain
from ..routes.routing import hal, api_url
from ..utils import delocalize_data

def get_public_root(domain, lang):
    rv = hal()
    rv._l('self', api_url('api.get_public_root'))
    rv._l('producelist:public_domain', api_url(
        'api.get_public_domain', domain_name="{domain}"), unquote=True, templated=True)
    rv._l('producelist:public_products', api_url(
        'api.get_public_products', domain=domain.name))
    rv._l('producelist:public_groups', api_url(
        'api.get_public_groups', domain=domain.name))
    rv._l('producelist:public_product_schema', api_url(
        'api.get_public_product_schema', domain=domain.name))
    rv._l('producelist:public_product_resources', api_url(
        'api.get_public_product_resources', domain=domain.name))
    rv._l('producelist:public_inquiries', api_url('api.post_public_inquiry'))
    rv._l('producelist:public_product', api_url(
        'api.get_public_product', product_id="{product_id}",
        domain=domain.name), unquote=True, templated=True)
    rv._l('producelist:domain_host_template', app.config.SUBDOMAIN_HOST_TEMPLATE,
          templated=True, unquote=True)
    rv._l('producelist:api_host', app.config.API_HOST)
    rv._l('producelist:account_host', app.config.ACCOUNT_HOST)
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
