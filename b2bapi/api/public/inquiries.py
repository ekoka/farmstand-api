from datetime import datetime
from vino import errors as vno_err

from ...db import db
from ...db.models.inquiries import Inquiry, InquiryProduct
from ...utils.uuid import clean_uuid
from ..routes.routing import json_abort

def post_public_inquiry(data, domain, lang, account):
    """
    - check that account has access to catalog
    - check data has contact information
    - check there's at least one product or a message
    - create new Inquiry
    - create InquiryProduct for each product
    """

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


    account_id = clean_uuid(account['account_id'])
    inq = Inquiry(
        domain_id=domain.domain_id,
        status='open',
        data={},
        account_id=account_id,
    )

    inq.products = _inquiry_products(data, account_id)
    inq.data['shipping'] = _inquiry_shipping(data)
    inq.data['billing'] = _inquiry_billing(data)
    inq.data['messages'] = _inquiry_messages(data, account_id)
    inq.data['lang'] = lang
    inq.data['email'] = {'sent': False, 'timestamp': None,}

    #for p in products:
    #    try:
    #        product_id = p.pop('product_id')
    #        inq.products.append(InquiryProduct(product_id=product_id, data=p))
    #    except KeyError:
    #        json_abort(400, {'error': 'Missing product_id'})

    db.session.add(inq)
    try:
        db.session.flush()
    except:
        db.session.rollback()
        json_abort(400, {'error': 'inquiry.error.invalid_lbl'})

    return {}, 200, []

def _inquiry_products(data, account_id):
    try:
        return [
            InquiryProduct(
            product_id=p['product_id'],
            quantity=p.get('quantity'),
            data={
                'messages': [
                    {
                        'account_id': account_id,
                        'comments': p.get('comments'),
                        'utc_timestamp': datetime.utcnow().timestamp(),
                    },
                ]
            }) for p in data.get('products')]
    except TypeError:
        return []

def _inquiry_shipping(data):
    return data.get('shipping_address', {})

def _inquiry_billing(data):
    return data.get('billing_address', {})

def _inquiry_messages(data, account_id):
    return [
        {
            'account_id': account_id,
            'comments': data.get('comments'),
            'utc_timestamp': datetime.utcnow().timestamp(),
        }
    ]
