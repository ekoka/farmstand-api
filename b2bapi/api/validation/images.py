from vino.api.schema import obj, arr, prim
from vino.processors import validating as vld
from vino.processors.validating import (
    required, rejectnull, allowempty, rejectempty)

from . import (set_tenant, check_bool, check_uuid4,  set_uuid, 
               upper, remove, set_default, set_value, has_any)

# TODO: add an extrafield blocker
# TODO: process blob here
add_source_image = obj(
    prim(required(override=set_tenant)).apply_to('tenant_id'),
    # TODO: this is where blob's signature should be assigned to source_image_id
    #prim(required(override=set_uuid)).apply_to('source_image_id'),
    # TODO: this is where metas should be set 

    #obj(~required, rejectempty(failsafe=set_value(None))).apply_to('meta'),
    # data = { "en" : { "caption" : null, "caption_html" : null, "tags": null},}
)

edit_source_image = obj()

ar_list = ('0:0', '1:1', '5:4', '4:3', '3:2', '16:9', '3:1')
size_list = ('large', 'medium', 'small', 'thumb') 
aspect_ratios = obj(
    arr(~required, prim(has_any(*ar_list)).apply_to(range(0,7))).apply_to(
        'aspect_ratios'),
    arr(~required, prim(has_any(*size_list)).apply_to(range(0,4))).apply_to(
        'sizes'),
)
