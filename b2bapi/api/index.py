from flask import current_app as app

from .routes.routing import hal, api_url

def get_index():
    rv = {
        'self': api_url('api.get_index'),
    }
    return rv, 200, []

def get_root():
    rv = hal()._l('self', api_url('api.get_root'))
    rv._l('producelist:plans', api_url('api.get_plans'))
    rv._l('producelist:id_token', api_url('api.post_id_token'))
    rv._l('producelist:access_token', api_url('api.post_access_token'))
    rv._l('producelist:signins', api_url('api.post_signin'))
    rv._l('producelist:accounts', api_url('api.post_account'))
    rv._l('producelist:profile', api_url('api.get_profile'))
    rv._l('producelist:account', api_url(
        'api.get_account', account_id='{account_id}'), templated=True,
        unquote=True)
    rv._l('producelist:domains', api_url('api.post_domain'))
    rv._l('producelist:domain', api_url('api.get_domain', domain_name='{domain}'),
        templated=True, unquote=True)
    rv._l('producelist:domain_name_check', api_url(
        'api.get_domain_name_check', name='{domain}'), templated=True,
        unquote=True)
    rv._l('producelist:public_root', api_url(
        'api.get_public_root', domain='{domain}'), templated=True,
        unquote=True)
    rv._l('producelist:domain_host_template', app.config[
        'SUBDOMAIN_HOST_TEMPLATE'], templated=True, unquote=True)
    rv._l('producelist:api_host', app.config['API_HOST'])
    rv._l('producelist:account_host', app.config['ACCOUNT_HOST'])
    rv._l('producelist:access_requests', api_url('api.post_access_request'))
    rv._l('producelist:access_request', api_url(
        'api.get_access_request', domain_id='{domain_id}'), templated=True,
        unquote=True)

    return rv.document, 200, []
