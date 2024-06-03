from .routes.routing import api_url
from ..service import product_types as pt_srv
from .utils import run_or_abort

def _product_type_resource(record):
    # api
    return {
        'self': api_url('api.get_product_type', product_type_id=record.product_type_id),
        'product_type_id': record.product_type_id,
        'name': record.name,
        'schema': record.schema, }

def get_product_type(product_type_id, domain):
    # api
    fnc = lambda:pt_srv.get_product_type(product_type_id, domain.domain_id)
    record = run_or_abort(fnc)
    return _product_type_resource(record), 200, []

def get_product_types(domain):
    # api
    product_types = run_or_abort(lambda: pt_srv.get_product_types(domain.domain_id))
    rv = {
        'self': api_url('api.get_product_types'),
        'product_types': [_product_type_resource(rec) for rec in product_types], }
    return rv, 200, []

def post_product_type(data, domain):
    # api
    fnc = lambda: pt_srv.create_product_type(domain.domain_id, data)
    record = run_or_abort(fnc)
    redirect_url = api_url(
        'api.get_product_type', product_type_id=record.product_type_id)
    rv = {
        'location': redirect_url,
        'product_type_id': record.product_type_id}
    return rv , 201, [('Location', redirect_url)]

def put_product_type(product_type_id, data, domain):
    # api
    fnc = lambda: pt_srv.update_product_type(product_type_id, domain.domain_id, data)
    record = run_or_abort(fnc)
    redirect_url = api_url(
        'api.get_product_type', product_type_id=record.product_type_id)
    rv = {
        'location':redirect_url,
        'product_type_id':record.product_type_id}
    return rv, 200, [('Location',redirect_url)]

def delete_product_type(product_type_id, domain):
    # api
    run_or_abort(lambda: pt_srv.delete_product_type(product_type_id, domain.domain_id))
    return {}, 200, []
