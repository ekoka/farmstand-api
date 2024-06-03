from ...public import inquiries as inq
from ..routing import (explicit_route as r, domain_member_authorization as domain_member,
                       domain_privacy_control as privacy_control)

r('/public/groups', inq.post_public_inquiry, methods=['POST'], expects_domain=True,
  expects_lang=True, authenticate=privacy_control, expects_data=True,
  authorize=domain_member, expects_account=True)
