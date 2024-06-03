from .routing import explicit_route as r
from .. import index as idx

r('/', idx.get_index, methods=['GET'], domained=False)
r('/root', idx.get_root, domained=False)
