from .. import users as usr
from .routing import explicit_route as r

r('/access-requests', usr.post_user_access_request, methods=['POST'], expects_data=True,
  domained=False, authenticate=True, expects_account=True)
r('/access-requests/<domain_name>', usr.get_user_access_request, domained=False,
  authenticate=True, expects_account=True)
r('/access-requests', usr.get_user_access_requests, domained=False, authenticate=True,
  expects_account=True)
# domain's access requests
r('/access-requests', usr.get_access_requests, authenticate=True)
r('/invites', usr.post_invite, methods=['POST'], authenticate=True)
# domain's invites
r('/invites', usr.get_invites, authenticate=True)
r('/invites', usr.get_user_invites, authenticate=True, domained=False, expects_account=True)
