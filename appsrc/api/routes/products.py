from .. import products as prd
from .routing import explicit_route as r, domain_owner_authorization as domain_owner_authz

#authorize=domain_owner_authz, expects_lang=True, readonly=True)
r('/products', prd.get_products, expects_params=True, expects_domain=True,
  expects_lang=True, readonly=True)
r('/product-resources', prd.get_product_resources, expects_params=True,
  expects_lang=True, expects_domain=True, authorize=domain_owner_authz,
  readonly=True)
# NOTE: just an alias route
r('/product-template', prd.get_product_schema, endpoint='get_product_template',
  expects_lang=True)
r('/product-schema', prd.get_product_schema, expects_lang=True)
r('/products/<product_id>/json', prd.get_product_json, authorize=domain_owner_authz,
  expects_domain=True)
r('/products/<product_id>/json', prd.put_product_json, methods=['put'],expects_domain=True,
  expects_data=True, authorize=domain_owner_authz,)
r('/products/<product_id>', prd.get_product, authorize=domain_owner_authz,
  expects_domain=True, expects_params=True, expects_lang=True)
r('/products', prd.post_product, methods=['POST'], expects_data=True, expects_lang=True)
r('/products/<product_id>', prd.put_product, methods=['PUT'], expects_data=True,
  authorize=domain_owner_authz, expects_domain=True, expects_lang=True)
r('/products/<product_id>/groups', prd.put_product_groups, methods=['PUT'],
  expects_domain=True, expects_data=True, authorize=domain_owner_authz)
r('/products/details', prd.get_product_details, expects_params=True, expects_domain=True,
  authorize=domain_owner_authz, expects_lang=True)
r('/products/<product_id>', prd.patch_product, methods=['PATCH'], expects_data=True,
  expects_domain=True, expects_lang=True, authorize=domain_owner_authz)
r('/products/<product_id>', prd.delete_product, methods=['DELETE'])
#r('/products', prd.get_products, methods=['GET'], expects_params=True, expects_lang=True)
# TODO: temporarily hardwired
#r('/product-templates/<product_type_id>', prd.get_product_template, methods=['GET'])
#r('/product-summary/<product_id>', prd.get_product_summary, expects_lang=True)
#r('/products/<product_id>', prd.get_product, expects_lang=True)
