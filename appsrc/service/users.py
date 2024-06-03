from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc

from ..db import db
from ..db.models.accounts import AccessRequest
from ..db.models.domains import Domain
from . import errors as err

def get_domain_by_name(domain_name):
    # service
    try:
        return Domain.query.filter_by(name=domain_name).one()
    except:
        raise err.NotFound('No domain matching that name')

def request_access(account_id, domain_name):
    # service
    # TODO: validate domain_name
    if domain_name is None:
        raise err.FormatError('No domain specified')
    domain = get_domain_by_name(domain_name)
    try:
        access_request = AccessRequest(
            domain_id=domain.domain_id,
            account_id=account_id,)
        db.session.add(access_request)
        db.session.flush()
    except sql_exc.IntegrityError:
        db.session.rollback()
        raise err.Conflict('Access to that domain already requested')
    except:
        db.session.rollback()
        raise err.FormatError('Could not request access to domain')
    return access_request

def get_user_access_request(account_id, domain_name):
    # service
    domain = get_domain_by_name(domain_name)
    try:
        return AccessRequest.query.filter_by(
            domain_id=domain.domain_id, account_id=account_id).one()
    except orm_exc.NoResultFound as e:
        raise err.NotFound('No access request matching that account and that domain')

def list_user_access_requests(account): pass

# ----------------------
# domain access requests
# ----------------------
def list_access_requests(): pass
# ----------------------
# domain invites
# ----------------------
def send_invite(): pass
def list_invites(): pass
def list_user_invites(account): pass
