from .routes.routing import hal, api_url
from .utils import run_or_abort
from ..service import inquiries as inq_srv


def get_inquiries(domain):
    # api
    fnc = lambda: inq_srv.get_inquiries(domain.domain_id)
    inquiries = run_or_abort(fnc)
    rv = hal()
    inquiry_url = api_url('api.get_inquiry', inquiry_id='{inquiry_id}')
    rv._l('self', api_url('api.get_inquiries'))
    rv._l('find', inquiry_url, unquote=True, templated=True)
    rv._embed('items', [_get_inquiry_resource(inq, partial=True) for inq in inquiries])
    return rv.document, 200, []

def _get_inquiry_resource(inq, partial=True):
    # api
    rv = hal()
    rv._l('self', api_url('api.get_inquiry', inquiry_id=inq.inquiry_id, partial=partial))
    rv._k('status', inq.status)
    rv._k('date', inq.dates.get(inq.status))
    if inq.data.get('billing_address'):
        ba = inq.data['billing_address']
        rv._k('contact', {
            'email': ba.get('email'),
            'name': ba.get('name'), })
    rv._k('inquiry_id', inq.inquiry_id.hex)
    if partial:
        rv._k('partial', partial)
    return rv.document

def get_inquiry(inquiry_id, domain, params):
    # api
    # in the meantime, while waiting for validation
    fnc = lambda: inq_srv.get_inquiry(inquiry_id, domain.domain_id)
    inquiry = run_or_abort(fnc)
    partial = int(params.get('partial', False))
    document = _get_inquiry_resource(inquiry, partial=partial)
    return document, 200, []

def put_inquiry(inquiry_id, data, domain):
    # api
    fnc = lambda: inq_srv.update_inquiry(inquiry_id, domain.domain_id, data)
    run_or_abort(fnc)
    return {}, 200, []

def delete_inquiry(inquiry_id, domain):
    # api
    fnc = lambda: inq_srv.delete_inquiry(inquiry_id, domain.domain_id)
    run_or_abort(fnc)
    return {}, 200, []
