from ..routing import explicit_route as r
from ...public import root

r('/public/root', root.get_public_root, expects_domain=True, expects_lang=True)
