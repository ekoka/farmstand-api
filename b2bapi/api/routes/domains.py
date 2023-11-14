from .routing import (
    explicit_route as r, domain_owner_authorization as domain_owner_authz,
    account_owner_authorization as account_owner_authz, _check_domain_ownership)
from .. import domains as dms

r('/domains', dms.post_domain, methods=['POST'], domained=False, expects_data=True,
  expects_access_token=True, expects_lang=True)
r('/domains', dms.get_domains, expects_access_token=True, domained=False, expects_lang=True,
  authenticate=True) #authorize=account_owner_authz)
r('/domain/<domain_name>', dms.get_domain, domained=False, expects_lang=True,
  authorize=_check_domain_ownership,)
r('/domain/<domain_name>', dms.put_domain, methods=['put'], domained=False,
  authorize=_check_domain_ownership, expects_lang=True, expects_data=True)
r('/domain-name-check', dms.get_domain_name_check, domained=False, expects_params=True)
r('/accounts', dms.post_domain_account, methods=['POST'], expects_data=True,
  expects_domain=True, authorize=domain_owner_authz)
r('/accounts/<account_id>', dms.delete_domain_account, expects_domain=True,
  methods=['DELETE'], authorize=domain_owner_authz)
r('/accounts', dms.get_domain_accounts, expects_domain=True, authorize=domain_owner_authz,
  expects_params=True)
r('/accounts/<account_id>', dms.get_domain_account, expects_domain=True,
  authorize=domain_owner_authz)
r('/access-requests', dms.post_access_request, methods=['POST'], expects_data=True,
  domained=False, authenticate=True, expects_account=True)
r('/access-requests/<domain_id>', dms.get_access_request, domained=False,
  expects_account=True, authenticate=True)
r('/access-requests', dms.get_domain_access_requests, expects_domain=True,
  authorize=domain_owner_authz, expects_lang=True)
r('/access-requests/<access_request_id>', dms.get_domain_access_request,
  authorize=domain_owner_authz, expects_lang=True)
r('/access-requests/<access_request_id>', dms.patch_domain_access_request,
  methods=['PATCH'], expects_data=True, authorize=domain_owner_authz)
