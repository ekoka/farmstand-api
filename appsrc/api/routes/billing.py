from .routing import explicit_route as r
from .. import billing as bill

r('/plans/<plan_id>', bill.get_plan, domained=False, expects_lang=True)
r('/plans', bill.get_plans, expects_params=True, domained=False, expects_lang=True)
r('/usage/<year>/<month>', bill.get_usage, domained=False, expects_access_token=True)
r('/payment-sources', bill.post_payment_source, methods=['POST'], authenticate=True,
  expects_access_token=True, domained=False, expects_data=True)
r('/payment-sources', bill.get_payment_sources, authenticate=True, expects_access_token=True,
  domained=False)
r('/payment-sources/<source_id>', bill.delete_payment_source, methods=['DELETE'],
  authenticate=True, expects_access_token=True, domained=False)
