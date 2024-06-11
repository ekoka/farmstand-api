from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from datetime import datetime

from . import errors as err
from ..db import db
from ..db.models.inquiries import Inquiry, InquiryProduct
from ..utils.uuid import clean_uuid

def save_inquiry(domain_id, account_id, data, lang):
    """
    - check that account has access to catalog
    - check data has contact information
    - check there's at least one product or a message
    - create new Inquiry
    - create InquiryProduct for each product
    """
    # service
    inq = Inquiry(
        domain_id=domain_id,
        account_id=account_id,
        status='open',
        products=_inquiry_products(data, account_id),
        data={
            'shipping': _inquiry_shipping(data),
            'billing': _inquiry_billing(data),
            'messages': _inquiry_messages(data, account_id),
            'lang': lang,
            'email': {'sent': False, 'timestamp': None,}, })
    try:
        db.session.add(inq)
        db.session.flush()
    except:
        db.session.rollback()
        raise err.FormatError('Could not save inquiry')
    return inq

def _inquiry_products(data, account_id):
    # service
    rv = []
    try:
        for p in data.get('products', []):
            inq_prod = InquiryProduct(
                product_id=p['product_id'],
                quantity=p.get('quantity'),)
            inq_prod.data = {
                'messages': [ {
                    'account_id': account_id,
                    'comments': p.get('comments'),
                    'utc_timestamp': datetime.utcnow().timestamp(), }, ] }
            rv.append(inq_prod)
    except TypeError:
        db.session.rollback()
        raise err.FormatError('Could not save product inquiry')

def _inquiry_shipping(data):
    return data.get('shipping_address', {})

def _inquiry_billing(data):
    return data.get('billing_address', {})

def _inquiry_messages(data, account_id):
    return [ {
        'account_id': account_id,
        'comments': data.get('comments'),
        'utc_timestamp': datetime.utcnow().timestamp(), } ]

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
