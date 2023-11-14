from .routing import explicit_route as r
from .. import product_fields as prd_fld

r('/fields', prd_fld.post_field, methods=['POST'], expects_data=True)
r('/fields/<field_id>', prd_fld.put_field, methods=['PUT'], expects_data=True)
r('/fields/<field_id>', prd_fld.delete_field, methods=['DELETE'])
r('/fields/<field_id>', prd_fld.get_field, methods=['GET'])
r('/fields', prd_fld.get_fields, methods=['GET'])
