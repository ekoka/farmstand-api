from flask import current_app as app
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db import db
from b2bapi.db.models.domains import Domain, DomainAccount
from b2bapi.utils.uuid import clean_uuid
from .._route import (route, json_abort, hal, api_url,)
from ..utils import delocalize_data

#from .validation.products import (add_product, edit_product)

def _get_domain(domain_name):
    try:
        return Domain.query.filter_by(name=domain_name).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error_code': 404, 'error': 'Domain not found'})

def _get_domain_resource(domain, lang):
    domain_url = api_url('api.get_public_domain', domain_name=domain.name)
    rv = hal()._l('self', domain_url)
    rv._k('name', domain.name)
    rv._k('creation_date', domain.creation_date.date())

    # include company info
    rv._k('data', delocalize_data(domain.data, Domain.localized_fields, lang))
    return rv.document

@route('/public/domain/<domain_name>', domained=False, expects_lang=True)
def get_public_domain(domain_name, lang):
    domain = _get_domain(domain_name=domain_name)
    return _get_domain_resource(domain, lang), 200, []
