from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc

from . import errors as err
from ..db import db
from ..db.models.inquiries import Inquiry
from ..utils.uuid import clean_uuid


def get_inquiries(domain_id):
    # service
    return Inquiry.query.filter_by(domain_id=domain_id).all()

def get_inquiry(inquiry_id, domain_id):
    # service
    notfound = lambda: err.NotFound("Inquiry not found")
    inquiry_id = clean_uuid(inquiry_id)
    try:
        if inquiry_id is None:
            raise notfound()
        return Inquiry.query.filter_by(inquiry_id=inquiry_id, domain_id=domain_id).one()
    except orm_exc.NoResultFound as e:
        raise notfound()

def db_flush():
    # service
    try:
        db.session.flush()
    except sql_exc.IntegrityError as e:
        db.session.rollback()
        raise err.FormatError('Could not save inquiry')

def update_inquiry(inquiry_id, domain_id, data):
    # service
    # TODO: validation
    # data = edit_inquiry.validate(data)
    inq = get_inquiry(inquiry_id, domain_id)
    #filters = data.pop('filters', [])
    fields = data.pop('fields', [])
    data.pop('data', None)
    inq.populate(**data)
    inq_fields = inq.data.setdefault('fields', [])
    def upsert_field(index, field):
        try:
            # update
            inq_fields[index]['en'] = field
        except IndexError:
            # insert
            inq_fields.append({'en': field})
    try:
        for i,fld in enumerate(fields):
            upsert_field(i, fld)
    except:
        db.session.rollback()
        raise err.FormatError('Could not update inquiry')
    #inq.filters = Filter.query.filter(Filter.filter_id.in_(filters)).all()
    db_flush()

def delete_inquiry(inquiry_id, domain_id):
    # service
    try:
        inq = get_inquiry(inquiry_id, domain_id)
        db.session.delete(inq)
        db.session.flush()
        #.inquiries.delete().where(
        #    (inquiries.c.domain_id==g.domain['domain_id'])&
        #    (inquiries.c.inquiry_id==inquiry_id)))
    except:
        pass
