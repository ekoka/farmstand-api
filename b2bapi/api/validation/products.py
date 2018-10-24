from vino.api.schema import obj, arr, prim
from vino.processors import validating as vld
from vino.processors.validating import required, rejectnull, allowempty

from . import (set_tenant, check_bool, check_uuid4,  set_uuid, 
               upper, remove, set_default, set_value)

field_schema = obj(
    prim().apply_to('name'),
    prim(required(default=set_value(False)), check_bool).apply_to(
         'searchable', 'display'),
    #prim(~required).apply_to('value'),
    #prim(~required, remove).apply_to('properties'),
)

field_arr = arr(~required,
                rejectnull(failsafe=set_value([])),
                field_schema.apply_to(range(0,20)), 
                allowempty,
               )


# TODO: add an extrafield blocker
add_product = obj(
    prim(required(override=set_tenant)).apply_to('tenant_id'),
    prim(required(default=set_uuid), rejectnull(failsafe=set_uuid), 
         check_uuid4).apply_to('product_id'),
    prim(required(default=set_value(False))).apply_to('publish'),
    # TODO make sure the variation_set exists
    prim(required(default=set_value(None))).apply_to('variation_set_id'),
    # overriding the more permissive requirement statement on `fields`
    arr(required(default=set_value([])), allowempty).apply_to('fields'),
    field_arr.apply_to('fields'),
)

# TODO: add an extrafield blocker
edit_product = obj(
    prim(~required, remove).apply_to(
        'product_id', 'tenant_id', 'self'),
    prim(~required, check_bool).apply_to('publish'),
    # TODO make sure the variation_set exists
    prim(~required).apply_to('variation_set_id'),
    field_arr.apply_to('fields'),
)

