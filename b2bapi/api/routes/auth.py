from .routing import explicit_route as r
from .. import auth

r('/signins', auth.post_signin, methods=['POST'], expects_data=True, domained=False)
