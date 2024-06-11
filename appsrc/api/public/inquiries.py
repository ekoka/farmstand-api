from vino import errors as vno_err

from ..utils import run_or_abort
from ...service import inquiries as inq_srv

def post_public_inquiry(data, domain, account, lang):
    # TODO: validate contact
    # try:
    #     data = validcontact.validate(data)
    # except vno_err.ValidationError as e:
    #     json_abort(400, {'error': 'inquiry.error.contact_info_lbl'})

    # TODO: validate has product or message
    # try:
    #     data = validproducts.validate(data)
    # except vno_err.ValidationError as e:
    #     json_abort(400, {'error': 'inquiry.error.invalid_lbl'})
    account_id = account.account_id
    domain_id = domain.domain_id
    fnc = lambda: inq_srv.save_inquiry(domain_id, account_id, data, lang)
    inquiry = run_or_abort(fnc)
    return {}, 200, []
