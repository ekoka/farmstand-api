from flask import redirect, g, current_app as app, abort, url_for

from ._route import route, hal
    
#@route('/<path:catchall>')
#def catchall(*a, **kw):
#    abort(404)

@route('/', methods=['GET'])
def get_index():
    rv = {
        'self': url_for('api.get_index'),
    }
    return rv, 200, []

@route('/root', tenanted=False)
def get_root():
    rv = hal()._l('self', url_for('api.get_root'))
    rv._l('simpleb2b:signins', url_for('api.post_signin'))
    rv._l('simpleb2b:accounts', url_for('api.post_account'))
    #rv._l('simpleb2b:account', '/api/v1/accounts/{account_id}', templated=True)
    rv._l('simpleb2b:account', url_for(
        'api.get_account', account_id='{account_id}'), templated=True, 
        unquote=True)
    rv._l('simpleb2b:tenants', url_for('api.post_tenant'))
    #._l('simpleb2b:tenant', '/api/v1/tenant/{tenant}', templated=True)
    rv._l('simpleb2b:tenant', url_for('api.get_tenant', tname='{tenant}'),
        templated=True, unquote=True)
    rv._l('simpleb2b:tenant-name-search', url_for(
        'api.get_tenant_name_search', name='{tenant}'), templated=True,
        unquote=True)
    rv._l('simpleb2b:public-root', url_for(
        'api.get_public_root', tenant='{tenant}'), templated=True, 
        unquote=True)
        #'/api/v1/tenant-name-search?name={tenant}', templated=True)
    return rv.document, 200, []
