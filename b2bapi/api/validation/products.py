from vino.api.schema import obj, arr, prim
from vino.processors import validating as vld
from vino.processors.validating import required, rejectnull, allowempty

from . import (set_domain, check_bool, check_uuid4,  set_uuid, 
               upper, remove, set_value)

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
    #TODO: we need a flexible validator that can handle values, arrays
    # and objects
    #prim(~required).apply_to('value'),
    #prim(~required, remove).apply_to('properties'),
)

field_arr = arr(
    # the array of fields is not required (inside the `data`)
    ~required,
    # if set to null the value will be set to `[]` as a failsafe
    rejectnull(failsafe=set_value([])),
    # each item in the range 0-20 of the array will be validated using the
    # `field_schema`
    field_schema.apply_to(range(0,20)),
    # the resulting field array can be empty 
    allowempty,
)

# TODO: add an extrafield blocker
add_product = obj(
    prim(required(override=set_domain)).apply_to('domain_id'),
    prim(required(default=set_uuid), rejectnull(failsafe=set_uuid), 
         check_uuid4).apply_to('product_id'),
    prim(required(default=set_value(False)), check_bool).apply_to('visible'),
    # TODO make sure the product_family exists
    #prim(required(default=set_value(None))).apply_to('product_family_id'),
    # overriding the more permissive requirement statement on `fields`
    field_arr.apply_to('fields')
)

# TODO: add an extrafield blocker
edit_product = obj(
    prim(~required, remove).apply_to(
        'product_id', 'domain_id', 'self'),
    prim(~required, check_bool).apply_to('visible'),
    # TODO make sure the product_family exists
    #prim(~required).apply_to('product_family_id'),
    #obj().apply_to('data'),
    field_arr.apply_to('fields')
)

edit_product_members = obj(
    prim(~required).apply_to('visible'),
    arr(
        ~required,
        obj(
            prim(required).apply_to('name', 'value', 'field_type'),
            prim(required(default=set_value(False)), check_bool).apply_to('display'),
        ).apply_to(range(0,20))
    ).apply_to('fields')
)
