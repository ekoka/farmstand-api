from vino.api.schema import obj, arr, prim
from vino.processors import validating as vld

from . import set_domain, check_uuid4,  set_uuid, upper, remove

# TODO: add an extrafield blocker
add_field = obj(
    prim(~vld.required, remove).apply_to('self'),
    prim(vld.required(override=set_domain)).apply_to('domain_id'),
    prim(vld.required(default=set_uuid), # if empty set_uuid will intervene
         vld.rejectnull(failsafe=set_uuid), # if null set_uuid will intervene
         check_uuid4,).apply_to('field_id'),
    prim().apply_to('name'),
    prim(upper).apply_to('field_type'),
    obj(vld.rejectnull).apply_to('schema'),
)

# TODO: add an extrafield blocker
edit_field = obj(
    prim(~vld.required, remove).apply_to('self'),
    prim(~vld.required, remove).apply_to(
        'name', 'field_type', 'field_id', 'domain_id'),
    obj(vld.rejectnull).apply_to('schema'),
)

add_product_type = obj(
    prim(~vld.required, remove).apply_to('self'),
    prim(vld.required(override=set_domain)).apply_to('domain_id'),
    prim(vld.required(default=set_uuid),
         vld.rejectnull(failsafe=set_uuid),
         check_uuid4,).apply_to(
        'product_type_id'),
    prim().apply_to('name'),
    obj(vld.allownull, vld.allowempty,
        arr(vld.allowempty, vld.allownull,
            obj().apply_to(30)).apply_to('fields')
       ).apply_to('schema'),
)

edit_product_type = obj(
    prim(~vld.required, remove).apply_to('self'),
    prim(~vld.required, remove).apply_to('product_type_id', 'domain_id'),
    prim().apply_to('name'),
    obj(arr(obj().apply_to(30)).apply_to('fields')).apply_to('schema'),
)
