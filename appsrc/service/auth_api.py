from .utils import run_or_abort

def post_signin(data):
    fnc = lambda: signin_srv.create_signin(data)
    run_or_abort(fnc)
    return {}, 200, []
