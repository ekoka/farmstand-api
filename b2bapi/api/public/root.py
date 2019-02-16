from flask import url_for

from .._route import route, hal, json_abort
    
#@route('/<path:catchall>')
#def catchall(*a, **kw):
#    abort(404)

@route('/public/root')
def get_public_root():
    rv = hal()
    rv._l('self', url_for('api.get_public_root'))
    rv._l('simpleb2b:public-filter-sets', url_for(
        'api.get_public_filter_sets'))
    rv._l('simpleb2b:public-product-schema', url_for(
        'api.get_public_product_schema'))
    rv._l('simpleb2b:public-products', url_for('api.get_public_products'))
    rv._l('simpleb2b:public-inquiries', url_for('api.post_public_inquiry'))
    rv._l('simpleb2b:public-product', url_for(
        'api.get_public_product', product_id="{product_id}"), unquote=True,
        templated=True)
        #'/api/v1/domain-name-search?name={domain}', templated=True)
    return rv.document, 200, []
