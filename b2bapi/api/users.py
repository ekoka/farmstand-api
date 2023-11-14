from ..db import db
from ..db.models.accounts import Account, AccessRequest, Invite
from ..db.models.domains import Domain, DomainAccount
from ..utils.uuid import clean_uuid
from .routes.routing import url_for, json_abort, hal

def _get_domain(domain_name):
    try:
        return Domain.query.filter_by(name=domain_name).one()
    except:
        json_abort(404, {'error': 'Merchant not found'})

def _get_access_request(domain_id, account_id):
    return Domain.query.filter_by(
        domain_id=domain_id, account_id=account_id).one()

def post_user_access_request(data, account):
    t = _get_domain(data.get('domain'))
    ar = AccessRequest(
        domain_id=t.domain_id,
        account_id=account['account_id'],)
    db.session.add(ar)
    try:
        db.session.flush()
    except:
        db.session.rollback()
        json_abort(400, {'error': 'Bad format'})
    rv = hal()
    rv._l('location', url_for(
        'api.get_user_access_request', domain_name=t.name))
    return rv.document, 200, []

def _user_access_request_resource(ar):
    rv = hal()
    t = ar.domain
    rv._l('self', url_for('api.get_user_access_request', domain_name=t.name))
    rv._k('domain', t.name)
    rv._k('status', ar.status)
    return rv.document

def get_user_access_request(domain_name, account):
    t = _get_domain(domain_name)
    ar = _get_access_request(
        account_id=account['account_id'], domain_id=t.domain_id)
    rv = _user_access_request_resource(ar)
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
