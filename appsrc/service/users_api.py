from .routes.routing import url_for, hal
from .utils import run_or_abort
from ..service import users as usr_srv

def post_user_access_request(data, account):
    # api
    domain = data.get('domain')
    account_id = account['account_id']
    run_or_abort(lambda: request_access(account_id, domain))
    rv = hal()
    rv._l('location', url_for('api.get_user_access_request', domain_name=domain))
    return rv.document, 200, []

def _user_access_request_resource(access_request):
    rv = hal()
    domain = access_request.domain
    rv._l('self', url_for('api.get_user_access_request', domain_name=domain.name))
    rv._k('domain', domain.name)
    rv._k('status', access_request.status)
    return rv.document

def get_user_access_request(domain_name, account):
    # api
    fnc = lambda: usr_srv.get_user_access_request(account['account_id'], domain_name)
    access_request = run_or_abort(fnc)
    rv = _user_access_request_resource(access_request)
    return rv, 200, []

def get_user_access_requests(account): pass

# ----------------------
# domain access requests
# ----------------------
def get_access_requests(): pass
# ----------------------
# domain invites
# ----------------------
def post_invite(): pass
def get_invites(): pass
def get_user_invites(account): pass
