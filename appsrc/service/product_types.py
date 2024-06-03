from sqlalchemy import exc
from sqlalchemy.orm import exc as orm_exc
from vino import errors as vno_err

from ..db import db
from ..db.models.meta import ProductType
from ..utils.uuid import clean_uuid
from .validation.meta import add_product_type, edit_product_type
from . import errors as err

def get_product_type(product_type_id, domain_id):
    # service
    try:
        product_type_id = clean_uuid(product_type_id)
        if product_type_id is None:
            raise orm_exc.NoResultFound()
        return ProductType.query.filter_by(
            domain_id=domain_id, product_type_id=product_type_id).one()
    except orm_exc.NoResultFound:
        raise err.NotFound(f'Product type {product_type_id} not found')

def get_product_types(domain_id):
    # service
    return ProductType.query.filter_by(domain_id=domain_id).all()

def create_product_type(domain_id, data):
    # service
    try:
        data = add_product_type.validate(data)
    except vno_err.ValidationErrorStack as e:
        raise err.FormatError(f'Invalid data: {str(e)}')
    data['domain_id'] = domain_id
    record = ProductType(**data)
    db.session.add(record)
    try:
        db.session.flush()
    except exc.IntegrityError as e:
        db.session.rollback()
        raise err.Conflict('Conflicting data.')
    return record

def update_product_type(product_type_id, domain_id, data):
    # service
    record = get_product_type(product_type_id, domain.domain_id)
    try:
        data = edit_product_type.validate(data)
        for k,v in data.items():
            setattr(record, k, v)
        db.session.flush()
    except vno_err.ValidationErrorStack as e:
        db.session.rollback()
        raise err.FormatError(f'Invalid input: {str(e)}')
    except exc.IntegrityError as e:
        db.session.rollback()
        raise err.Conflict(f'Conflicting input: {str(e)}')
    return record

def delete_product_type(product_type_id, domain_id):
    # service
    product_types_tbl = ProductType.__table__
    try:
        db.session.execute(product_types_tbl.delete().where(
            (product_types_tbl.c.domain_id==domain_id) &
            (product_types_tbl.c.product_type_id==product_type_id)))
    except:
        pass
