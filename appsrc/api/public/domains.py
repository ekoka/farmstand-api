from sqlalchemy.orm import exc as orm_exc

from ...db.models.domains import Domain
from ..routes.routing import json_abort, hal, api_url
from ..utils import delocalize_data
from ...service import domains as dom_srv

#from .validation.products import (add_product, edit_product)

def _get_domain_resource(domain, lang):
    domain_url = api_url('api.get_public_domain', domain_name=domain.name)
    rv = hal()._l('self', domain_url)
    rv._k('name', domain.name)
    rv._k('creation_date', domain.creation_date.date())
    # include company info
    rv._k('data', delocalize_data(domain.data, Domain.localized_fields, lang))
    return rv.document

def get_public_domain(domain_name, lang):
    domain = dom_srv.get_domain_by_name(domain_name)
    return _get_domain_resource(domain, lang), 200, []
