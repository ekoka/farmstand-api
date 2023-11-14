from .. import accounts as acc
from .routing import (
    explicit_route as r, account_owner_authorization as account_owner_authz,
    id_token_authentication)


r('/id-token', acc.post_id_token, methods=['POST'], domained=False, expects_data=True)
r('/access-token', acc.post_access_token, methods=['POST'], domained=False,
  expects_data=True, authenticate=id_token_authentication, expects_account=True)
r('/profile', acc.get_profile, methods=['GET'], domained=False, authenticate=True,
  expects_access_token=True)
r('/access-token', acc.delete_access_token, methods=['DELETE'], domained=False,
  authenticate=True, expects_access_token=True)
r('/accounts', acc.post_account, methods=['POST'], domained=False, expects_data=True)
r('/accounts/<account_id>', acc.get_account, domained=False, authorize=account_owner_authz,
  expects_lang=True)
r('/accounts/<account_id>', acc.put_account, methods=['PUT'], domained=False,
  authorize=account_owner_authz, expects_data=True, expects_lang=True)
