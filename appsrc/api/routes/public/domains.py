from ..routing import explicit_route as r
from ...public import domains as dmn

r('/public/domain/<domain_name>', dmn.get_public_domain, domained=False, expects_lang=True)
