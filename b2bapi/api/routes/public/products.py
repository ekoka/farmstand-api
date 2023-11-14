from ..routing import (explicit_route as r, domain_member_authorization as domain_member,
                       domain_privacy_control as privacy_control)
from ...public import products as prd

r('/public/groups/<group_id>', prd.get_public_group, expects_domain=True, expects_lang=True,
       authenticate=privacy_control, authorize=domain_member)
r('/public/groups', prd.get_public_groups, expects_domain=True, expects_lang=True,
       authenticate=privacy_control, authorize=domain_member)
r('/public/products', prd.get_public_products, expects_params=True, expects_domain=True,
      authenticate=privacy_control, authorize=domain_member,)
r('/public/product-resources', prd.get_public_product_resources, expects_params=True, expects_lang=True,
       expects_domain=True, authenticate=privacy_control,
       authorize=domain_member)
r('/public/products/<product_id>', prd.get_public_product, expects_domain=True,
       expects_params=True, authenticate=privacy_control,
       authorize=domain_member,)

# --------------
# Product Schema
# -------------
r('/public/product-schema', prd.get_public_product_schema, expects_domain=True,
       authenticate=privacy_control, authorize=domain_member)
