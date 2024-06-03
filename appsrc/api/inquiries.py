from flask import current_app as app
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc

from ..db import db
from ..db.models.inquiries import Inquiry, InquiryProduct
from ..utils.uuid import clean_uuid
from .routes.routing import json_abort, hal, api_url


def get_inquiries(domain):
    domain_id = domain.domain_id
    q = Inquiry.query.filter_by(domain_id=domain_id)
    inquiries = q.all()
    inquiry_url = api_url('api.get_inquiry', inquiry_id='{inquiry_id}')
    rv = hal()
    rv._l('self', api_url('api.get_inquiries'))
    rv._l('find', inquiry_url, unquote=True, templated=True)

    rv._embed('items', [_get_inquiry_resource(i, partial=True)
                       for i in inquiries])
    return rv.document, 200, []

def _get_inquiry_resource(i, partial=True):
    rv = hal()
    rv._l('self', api_url('api.get_inquiry', inquiry_id=i.inquiry_id,
                          partial=partial))

    rv._k('status', i.status)
    rv._k('date', i.dates.get(i.status))
    if i.data.get('billing_address'):
        b = i.data['billing_address']
        rv._k('contact', {
            'email': b.get('email'),
            'name': b.get('name'),
        })
    rv._k('inquiry_id', i.inquiry_id.hex)
    if partial:
        rv._k('partial', partial)
    return rv.document

def _get_inquiry(inquiry_id, domain_id):
    inquiry_id = clean_uuid(inquiry_id)
    try:
        if inquiry_id is None:
            raise orm_exc.NoResultFound()
        return Inquiry.query.filter_by(inquiry_id=inquiry_id,
                                       domain_id=domain_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error': 'Inquiry Not Found'})

def get_inquiry(inquiry_id, domain, params):
    # in the meantime, while waiting for validation
    partial = int(params.get('partial', False))
    inquiry = _get_inquiry(inquiry_id, domain.domain_id)
    document = _get_inquiry_resource(inquiry, partial=partial)
    return document, 200, []

def db_flush():
    try:
        db.session.flush()
    except sql_exc.IntegrityError as e:
        raise
        db.session.rollback()
        json_abort(400, {'error': 'Could not save record. Verify format.'})


def put_inquiry(inquiry_id, data, domain):
    # TODO: validation
    # data = edit_inquiry.validate(data)
    i = _get_inquiry(inquiry_id, domain.domain_id)

    filters = data.pop('filters', [])
    fields = data.pop('fields', [])
    data.pop('data', None)
    i.populate(**data)

    try:
        for i,f in enumerate(fields):
            try:
                val = i.data.setdefault('fields', [])[i]
                val['en'] = f
            except IndexError:
                val = {'en': f}
                i.data.setdefault('fields', []).append(val)
    except:
        json_abort(400, {'error':'Bad Format'})

    i.filters = Filter.query.filter(Filter.filter_id.in_(filters)).all()

    db_flush()
    return {}, 200, []

def delete_inquiry(inquiry_id, domain):
    try:
        i = _get_inquiry(inquiry_id, domain.domain_id)
        db.session.delete(i)
        db.session.flush()
        #.inquiries.delete().where(
        #    (inquiries.c.domain_id==g.domain['domain_id'])&
        #    (inquiries.c.inquiry_id==inquiry_id)))
    except:
        pass
    return {}, 200, []
