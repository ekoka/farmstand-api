from .. import inquiries as inq
from .routing import explicit_route as r

r('/inquiries', inq.get_inquiries, expects_domain=True, authenticate=True)
r('/inquiries/<inquiry_id>', inq.get_inquiry, authenticate=True, expects_domain=True,
  expects_params=True)
r('/inquiries/<inquiry_id>', inq.put_inquiry, methods=['PUT'], expects_data=True,
  authenticate=True, expects_domain=True)
r('/inquiries/<inquiry_id>', inq.delete_inquiry, methods=['DELETE'], authenticate=True,
  expects_domain=True)
