from flask import current_app as app

from .routes.routing import hal, api_url

def get_index():
    rv = {
        'self': api_url('api.get_index'),
    }
    return rv, 200, []

def get_root():
    rv = hal()._l('self', api_url('api.get_root'))
    rv._l(f'{app.config.API_NAMESPACE}:plans', api_url('api.get_plans'))
    rv._l(f'{app.config.API_NAMESPACE}:id_token', api_url('api.post_id_token'))
    rv._l(f'{app.config.API_NAMESPACE}:access_token', api_url('api.post_access_token'))
    rv._l(f'{app.config.API_NAMESPACE}:signins', api_url('api.post_signin'))
    rv._l(f'{app.config.API_NAMESPACE}:accounts', api_url('api.post_account'))
    rv._l(f'{app.config.API_NAMESPACE}:profile', api_url('api.get_profile'))
    rv._l(f'{app.config.API_NAMESPACE}:account', api_url(
        'api.get_account', account_id='{account_id}'), templated=True,
        unquote=True)
    rv._l(f'{app.config.API_NAMESPACE}:domains', api_url('api.post_domain'))
    rv._l(f'{app.config.API_NAMESPACE}:domain', api_url('api.get_domain', domain_name='{domain}'),
        templated=True, unquote=True)
    rv._l(f'{app.config.API_NAMESPACE}:domain_name_check', api_url(
        'api.get_domain_name_check', name='{domain}'), templated=True,
        unquote=True)
    rv._l(f'{app.config.API_NAMESPACE}:public_root', api_url(
        'api.get_public_root', domain='{domain}'), templated=True,
        unquote=True)
    rv._l(f'{app.config.API_NAMESPACE}:domain_host_template', app.config[
        'SUBDOMAIN_HOST_TEMPLATE'], templated=True, unquote=True)
    rv._l(f'{app.config.API_NAMESPACE}:api_host', app.config['API_HOST'])
    rv._l(f'{app.config.API_NAMESPACE}:account_host', app.config['ACCOUNT_HOST'])
    rv._l(f'{app.config.API_NAMESPACE}:access_requests', api_url('api.post_access_request'))
    rv._l(f'{app.config.API_NAMESPACE}:access_request', api_url(
        'api.get_access_request', domain_id='{domain_id}'), templated=True,
        unquote=True)

    return rv.document, 200, []
