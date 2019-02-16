import simplejson as json
import datetime

from flask import redirect, g, current_app as app, abort, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db import db
from b2bapi.db.models.inquiries import Inquiry, InquiryProduct
from b2bapi.utils.uuid import clean_uuid
from .._route import route, json_abort, hal


@route('/public/inquiries', methods=['POST'], expects_data=True, 
       expects_domain=True)
def post_public_inquiry(data, domain):
    # TODO: validation
    if not data.get('billing_address'):
        json_abort(400, {'error': 'Missing billing address'})
        
    # required
    for v in ['email', 'first_name', 'last_name']:
        if not data['billing_address'].get(v):
            json_abort(400, {'error': f'Missing field {v}'})

    try:
        products = data.pop('products')
        if not products:
            raise KeyError
    except KeyError:
        json_abort(400, {'error': 'No products sent'})


    inq = Inquiry(
        data=data, 
        domain_id=domain.domain_id, 
        dates={'created': datetime.datetime.utcnow().isoformat()},
        status='created',
    )
    for p in products:
        try:
            product_id = p.pop('product_id')
            inq.products.append(InquiryProduct(product_id=product_id, data=p))
        except KeyError:
            json_abort(400, {'error': 'Missing product_id'})

    db.session.add(inq)
    try:
        db.session.flush()
    except:
        db.session.rollback()
        json_abort(400, {'error': 'missing field'})

    return {}, 200, []
        
