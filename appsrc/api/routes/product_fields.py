from .routing import explicit_route as r
from .. import product_fields as prd_fld

r('/fields', prd_fld.post_field, methods=['POST'], expects_data=True, expects_domain=True,
  expects_lang=True)
r('/fields/<field_id>', prd_fld.put_field, methods=['PUT'], expects_data=True,
  expects_domain=True, expects_lang=True)
r('/fields/<field_id>', prd_fld.delete_field, methods=['DELETE'], expects_domain=True)
r('/fields/<field_id>', prd_fld.get_field, methods=['GET'], expects_domain=True,
  expects_lang=True)
r('/fields', prd_fld.get_fields, methods=['GET'], expects_domain=True, expects_lang=True)
