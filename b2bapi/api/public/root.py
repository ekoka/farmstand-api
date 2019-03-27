from flask import url_for

from .._route import route, hal, json_abort
    
#@route('/<path:catchall>')
#def catchall(*a, **kw):
#    abort(404)

@route('/public/root', expects_domain=True)
def get_public_root(domain):
    rv = hal()
    rv._l('self', url_for('api.get_public_root'))
    rv._l('productlist:public_products', url_for(
        'api.get_public_products', domain=domain.name))
    rv._l('productlist:public_product_schema', url_for(
        'api.get_public_product_schema', domain=domain.name))
    #TODO: later when implementing inquiar
    #rv._l('simpleb2b:public-inquiries', url_for('api.post_public_inquiry'))
    rv._l('productlist:public_product', url_for(
        'api.get_public_product', product_id="{product_id}",
        domain=domain.name), unquote=True, templated=True)
        #'/api/v1/domain-name-search?name={domain}', templated=True)
    return rv.document, 200, []
