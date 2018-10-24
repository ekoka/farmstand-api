from vino.api.schema import obj, arr, prim
from vino.processors import validating as vld
from vino import errors as vno_err

from . import set_tenant, check_uuid4,  set_uuid, upper, remove, set_value

def check_at_least_one_signin_present(data, state):
    if not data.get('email') and not data.get('google_signin'):
        raise vno_err.ValidationError(
            'A signin option is required to create a new account.')
    return data

def check_email_format(data, state):
    #TODO
    if not '@' in data:
        raise vno_err.ValidationError('Email format does not seem valid')
    return data

# TODO: add an extrafield blocker
new_account = obj(
    prim(vld.optional, remove).apply_to('self'),
    prim(vld.optional, remove).apply_to('tenant_id'),
    prim(vld.required(default=set_uuid), # if empty set_uuid will intervene
         vld.rejectnull(failsafe=set_uuid), # if null set_uuid will intervene
         check_uuid4,).apply_to('account_id'),
    prim(vld.optional, check_email_format).apply_to('email'),
    prim(vld.optional, vld.allowempty, vld.allownull).apply_to('google_signin'),
    check_at_least_one_signin_present,
    prim(vld.optional, vld.allownull, vld.allowempty).apply_to('name'),
    obj(vld.required(default=set_value({}), override=set_value({})), 
        vld.allowempty, vld.allownull).apply_to('meta'),
    prim(vld.optional, remove).apply_to('authkey'),
)

# TODO: add an extrafield blocker
edit_field = obj(
    prim(~vld.required, remove).apply_to('self'),
    prim(~vld.required, remove).apply_to(
        'name', 'field_type', 'field_id', 'tenant_id'),
    obj(vld.rejectnull).apply_to('schema'),
)

add_product_type = obj(
    prim(~vld.required, remove).apply_to('self'),
    prim(vld.required(override=set_tenant)).apply_to('tenant_id'),
    prim(vld.required(default=set_uuid), 
         vld.rejectnull(failsafe=set_uuid),
         check_uuid4,).apply_to(
        'product_type_id'),
    prim().apply_to('name'),
    obj(arr(obj().apply_to(30)).apply_to('fields')).apply_to('schema'),
)

edit_product_type = obj(
    prim(~vld.required, remove).apply_to('self'),
    prim(~vld.required, remove).apply_to('product_type_id', 'tenant_id'),
    prim().apply_to('name'),
    obj(arr(obj().apply_to(30)).apply_to('fields')).apply_to('schema'),
)
