from .. import product_types as prd_typ
from .routing import explicit_route as r

r('/product-types/<product_type_id>', prd_typ.get_product_type, expects_domain=True)
r('/product-types', prd_typ.get_product_types, expects_domain=True)
r('/product-types', prd_typ.post_product_type, methods=['POST'], expects_data=True,
  expects_domain=True)
r('/product-types/<product_type_id>', prd_typ.put_product_type, methods=['PUT'],
  expects_data=True, expects_domain=True)
r('/product-types/<product_type_id>', prd_typ.delete_product_type, methods=['DELETE'],
  expects_domain=True)
