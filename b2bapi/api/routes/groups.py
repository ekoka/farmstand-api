from .routing import explicit_route as r, domain_owner_authorization as domain_owner_authz
from .. import groups as grp

r('/groups', grp.get_groups, expects_domain=True, expects_lang=True,
  authorize=domain_owner_authz)
r('/group-resources', grp.get_group_resources, expects_domain=True, expects_params=True,
  expects_lang=True, authorize=domain_owner_authz)
r('/groups', grp.post_group, methods=['POST'], expects_domain=True, expects_data=True,
  expects_lang=True, authorize=domain_owner_authz)
r('/groups/<group_id>', grp.put_group, methods=['PUT'], expects_data=True, expects_lang=True,
  expects_domain=True, authorize=domain_owner_authz)
r('/groups/<group_id>', grp.get_group, expects_domain=True, expects_lang=True,
  authorize=domain_owner_authz)
r('/groups/<group_id>', grp.delete_group, methods=['DELETE'], expects_domain=True,
  authorize=domain_owner_authz)
r('/groups/<group_id>/options', grp.post_group_option, methods=['POST'], expects_lang=True,
  expects_domain=True, expects_data=True, authorize=domain_owner_authz)
r('/groups/<group_id>/options/<group_option_id>', grp.get_group_option, expects_domain=True,
  authorize=domain_owner_authz, expects_lang=True)
r('/groups/<group_id>/options/<group_option_id>', grp.put_group_option, expects_domain=True,
  expects_lang=True, expects_data=True, authorize=domain_owner_authz)
r('/groups/<group_id>/options/<group_option_id>', grp.delete_group_option,
  expects_domain=True, authorize=domain_owner_authz)
r('/groups/<group_id>/options/<group_option_id>/products', grp.put_group_option_products,
  methods=['PUT'], expects_domain=True, expects_data=True, authorize=domain_owner_authz)
