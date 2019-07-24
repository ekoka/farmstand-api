from flask import g, current_app as app, jsonify, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db.models.accounts import Account, AccessRequest, Invite
from b2bapi.db.models.domains import Domain, DomainAccount
from b2bapi.db import db
from b2bapi.utils.uuid import clean_uuid
from ._route import route, url_for, json_abort, hal

def _get_domain(domain_name):
    try:
        return Domain.query.filter_by(name=domain_name).one()
    except:
        json_abort(404, {'error': 'Merchant not found'})

def _get_access_request(domain_id, account_id):
    return Domain.query.filter_by(
        domain_id=domain_id, account_id=account_id).one()

@route('/access-requests', methods=['POST'], expects_data=True, domained=False,
       authenticate=True, expects_account=True)
def post_user_access_request(data, account):
    t = _get_domain(data.get('domain'))
    ar = AccessRequest(
        domain_id=t.domain_id,
        account_id=account['account_id'],
    )
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

@route('/access-requests/<domain_name>', domained=False, authenticate=True,
       expects_account=True)
def get_user_access_request(domain_name, account):
    t = _get_domain(domain_name)
    ar = _get_access_request(
        account_id=account['account_id'], domain_id=t.domain_id)
    rv = _user_access_request_resource(ar)
    return rv, 200, []

     

@route('/access-requests', domained=False, authenticate=True, 
       expects_account=True)
def get_user_access_requests(account):
    pass

# domain's access requests 
@route('/access-requests', authenticate=True)
def get_access_requests():
    pass

@route('/invites', methods=['POST'], authenticate=True)
def post_invite():
    pass

# domain's invites
@route('/invites', authenticate=True)
def get_invites():
    pass

@route('/invites', authenticate=True, domained=False, expects_account=True)
def get_user_invites(account):
    pass
