from .utils import run_or_abort
from ..service import auth as auth_srv

def post_signin(data):
    fnc = lambda: auth_srv.create_signin(data)
    run_or_abort(fnc)
    return {}, 200, []
