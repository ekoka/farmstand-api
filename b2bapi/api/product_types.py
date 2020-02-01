import uuid
from flask import g, abort, current_app as app, url_for
from sqlalchemy import exc
from sqlalchemy.orm import exc as orm_exc
from vino import errors as vno_err

from b2bapi.db.models.meta import ProductType
from b2bapi.db import db
from b2bapi.utils.uuid import clean_uuid
from .validation.meta import add_product_type, edit_product_type
from ._route import route, api_url

def product_type_resource(record):
    rv = {
        'self': api_url('api.get_product_type', 
                       product_type_id=record.product_type_id),
        'product_type_id': record.product_type_id,
        'name': record.name,
        'schema': record.schema,
    }
    return rv

def _get_product_type(product_type_id):
    try:
        product_type_id = clean_uuid(product_type_id)
        if product_type_id is None:
            raise orm_exc.NoResultFound()
        return ProductType.query.filter_by(
            domain_id=g.domain['domain_id'],
            product_type_id=product_type_id).one()
    except orm_exc.NoResultFound:
        abort(404)

@route('/product-types/<product_type_id>')
def get_product_type(product_type_id):
    record = _get_product_type(product_type_id)
    return product_type_resource(record), 200, []

@route('/product-types')
def get_product_types():
    rv = {
        'self': api_url('api.get_product_types'),
        'product_types': [
            product_type_resource(rec)
            #{'name': rec.name,
            # 'product_type_id': rec.product_type_id,
            # 'url': api_url('api.get_product_type',
            #               product_type_id=rec.product_type_id),
            #} 
            for rec in ProductType.query.all() ],
    }
    return rv, 200, []

@route('/product-types', methods=['POST'], expects_data=True)
def post_product_type(data):
    try:
        data = add_product_type.validate(data)
    except vno_err.ValidationErrorStack as e:
        abort(400, str(e))

    record = ProductType(**data)
    db.session.add(record)

    try:
        db.session.flush()
    except exc.IntegrityError as e:
        db.session.rollback()
        abort(409)

    redirect_url = api_url('api.get_product_type', 
                          product_type_id=record.product_type_id)
    return ({'location':redirect_url,
             'product_type_id':record.product_type_id},
            201, [('Location',redirect_url)])

@route('/product-types/<product_type_id>', methods=['PUT'], 
       expects_data=True)
def put_product_type(product_type_id, data):
    app.logger.info(product_type_id)
    record = _get_product_type(product_type_id)

    try:
        data = edit_product_type.validate(data)
        for k,v in data.items():
            setattr(record, k, v)
        db.session.flush()
    except vno_err.ValidationErrorStack as e:
        abort(400, str(e))
    except exc.IntegrityError as e:
        db.session.rollback()
        abort(409)

    redirect_url = api_url('api.get_product_type',
                          product_type_id=record.product_type_id)
    return ({'location':redirect_url, 
             'product_type_id':record.product_type_id}, 200,
            [('Location',redirect_url)])

@route('/product-types/<product_type_id>', methods=['DELETE'])
def delete_product_type(product_type_id):
    product_types = ProductType.__table__
    db.session.execute(product_types.delete().where(
        (product_types.c.domain_id==g.domain['domain_id'])&
        (product_types.c.product_type_id==product_type_id)))
    return ({}, 200, [])

