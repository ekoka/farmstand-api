from flask import redirect, g, current_app as app, abort, url_for

from ._route import route, hal
    
#@route('/<path:catchall>')
#def catchall(*a, **kw):
#    abort(404)

@route('/', methods=['GET'], domained=False)
def get_index():
    rv = {
        'self': url_for('api.get_index'),
    }
    return rv, 200, []

@route('/root', domained=False)
def get_root():
    rv = hal()._l('self', url_for('api.get_root'))
    rv._l('productlist:plans', url_for('api.get_plans'))
    rv._l('productlist:access_token', url_for('api.post_access_token'))
    rv._l('productlist:signins', url_for('api.post_signin'))
    rv._l('productlist:accounts', url_for('api.post_account'))
    #rv._l('productlist:account', '/api/v1/accounts/{account_id}', templated=True)
    rv._l('productlist:account', url_for(
        'api.get_account', account_id='{account_id}'), templated=True,
        unquote=True)
    rv._l('productlist:domains', url_for('api.post_domain'))
    #._l('productlist:domain', '/api/v1/domain/{domain}', templated=True)
    rv._l('productlist:domain', url_for('api.get_domain', domain_name='{domain}'),
        templated=True, unquote=True)
    rv._l('productlist:domain-name-check', url_for(
        'api.get_domain_name_check', name='{domain}'), templated=True,
        unquote=True)
    rv._l('productlist:public-root', url_for(
        'api.get_public_root', domain='{domain}'), templated=True, 
        unquote=True)
        #'/api/v1/domain-name-search?name={domain}', templated=True)
    return rv.document, 200, []
