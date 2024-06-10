from ..utils.uuid import clean_uuid
from ..service import product_fields as fld_srv
from .routes.routing import api_url
from .utils import run_or_abort

def post_field(data, domain, lang):
    # api
    field = run_or_abort(lambda: fld_srv.create_field(domain.domain_id, data, lang))
    rv = {
        'location':redirect_url,
        'field_id':clean_uuid(field.field_id), }
    return rv, 201, [('Location', redirect_url)]

def put_field(field_id, data, domain, lang):
    # api
    fnc = lambda: fld_srv.update_field(field_id, domain.domain_id, data, lang)
    run_or_abort(fnc)
    return {}, 200, []

def delete_field(field_id, domain):
    # api
    run_or_abort(lambda: fld_srv.delete_field(field_id, domain.domain_id))
    return {}, 200, []

def _field_resource(field, lang):
    # api
    return {
        'self': api_url('api.get_field', field_id=clean_uuid(field.field_id)),
        'field_id': clean_uuid(field.field_id),
        'name': field.name,
        'field_type': field.field_type,
        'schema': field.get_schema(lang), }

def get_field(field_id, domain, lang):
    # api
    fnc = lambda: fld_srv.get_field(field_id, domain.domain_id)
    field = run_or_abort(fnc)
    return _field_resource(field, lang), 200, []

def get_fields(domain, lang):
    # api
    fields = run_or_abort(lambda: fld_srv.get_fields(domain.domain_id))
    rv = {
        'self': api_url('api.get_fields'),
        'fields': [_field_resource(fld, lang) for fld in fields], }
    return rv, 200, []
