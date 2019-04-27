from flask import redirect, g, current_app as app, abort, url_for

from ._route import route, hal, api_url
    
#@route('/<path:catchall>')
#def catchall(*a, **kw):
#    abort(404)

@route('/', methods=['GET'], domained=False)
def get_index():
    rv = {
        'self': api_url('api.get_index'),
    }
    return rv, 200, []

@route('/root', domained=False)
def get_root():
    rv = hal()._l('self', api_url('api.get_root'))
    rv._l('productlist:plans', api_url('api.get_plans'))
    rv._l('productlist:id_token', api_url('api.post_id_token'))
    rv._l('productlist:access_token', api_url('api.post_access_token'))
    rv._l('productlist:signins', api_url('api.post_signin'))
    rv._l('productlist:accounts', api_url('api.post_account'))
    #rv._l('productlist:account', '/api/v1/accounts/{account_id}', templated=True)
    rv._l('productlist:profile', api_url('api.get_profile'))
    rv._l('productlist:account', api_url(
        'api.get_account', account_id='{account_id}'), templated=True,
        unquote=True)
    rv._l('productlist:domains', api_url('api.post_domain'))
    #._l('productlist:domain', '/api/v1/domain/{domain}', templated=True)
    rv._l('productlist:domain', api_url('api.get_domain', domain_name='{domain}'),
        templated=True, unquote=True)
    rv._l('productlist:domain_name_check', api_url(
        'api.get_domain_name_check', name='{domain}'), templated=True,
        unquote=True)
    rv._l('productlist:public_root', api_url(
        'api.get_public_root', domain='{domain}'), templated=True, 
        unquote=True)
        #'/api/v1/domain-name-search?name={domain}', templated=True)
    rv._l('productlist:domain_host_template', app.config[
        'SUBDOMAIN_HOST_TEMPLATE'], templated=True, unquote=True)
    rv._l('productlist:api_host', app.config['API_HOST'])
    rv._l('productlist:account_host', app.config['ACCOUNT_HOST'])

    return rv.document, 200, []
