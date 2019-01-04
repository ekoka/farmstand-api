from vino.api.schema import obj, arr, prim
from vino.processors import validating as vld
from vino.processors.validating import required, rejectnull, allowempty

from . import (set_tenant, check_bool, check_uuid4,  set_uuid, 
               upper, remove, set_default, set_value)

# each field is an object
field_schema = obj( 
    # it has a name
    prim().apply_to('name'), 
    # it has a `searchable` and `display` attribute that are both
    # required. If they're not present, they're set to `False` by
    # default.
    # They must be a boolean.
    prim(required(default=set_value(False)), check_bool).apply_to(
         'searchable', 'display'), 
    #prim(~required).apply_to('value'),
    #prim(~required, remove).apply_to('properties'),
)

field_arr = arr(
    # the array of fields is not required 
    ~required,
    # if set to null the value will be set to `[]` as a failsafe
    rejectnull(failsafe=set_value([])),
    # each item in the range 0-20 of the array will be applied the
    # `field_schema` 
    field_schema.apply_to(range(0,20)), 
    # the fields array can be empty 
    allowempty,
)

#data_val = obj(
#    arr(required(default=set_value([])), allowempty).apply_to('fields'),
#    field_arr.apply_to('fields'),
#).apply_to('data')

data_val = obj(
    prim().apply_to('name', 'description', 'number')
).apply_to('data')


# TODO: add an extrafield blocker
add_product = obj(
    prim(required(override=set_tenant)).apply_to('tenant_id'),
    prim(required(default=set_uuid), rejectnull(failsafe=set_uuid), 
         check_uuid4).apply_to('product_id'),
    prim(required(default=set_value(False)), check_bool).apply_to('visible'),
    prim(required(default=set_value(True)), check_bool).apply_to('available'),
    # TODO make sure the product_family exists
    #prim(required(default=set_value(None))).apply_to('product_family_id'),
    # overriding the more permissive requirement statement on `fields`
    data_val,
)

# TODO: add an extrafield blocker
edit_product = obj(
    prim(~required, remove).apply_to(
        'product_id', 'tenant_id', 'self'),
    prim(~required, check_bool).apply_to('publish'),
    # TODO make sure the product_family exists
    #prim(~required).apply_to('product_family_id'),
    field_arr.apply_to('fields'),
)

