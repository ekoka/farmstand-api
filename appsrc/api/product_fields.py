from flask import g, abort, current_app as app
from sqlalchemy.orm import exc as orm_exc
from vino import errors as vno_err

from ..db import db
from ..db.models.meta import Field
from ..utils.uuid import clean_uuid
from .validation.meta import add_field, edit_field
from .routes.routing import api_url

def _get_field(field_id):

    field_id = clean_uuid(field_id)

    try:
        if field_id is None:
            abort(404)
        return Field.query.filter_by(
            domain_id=g.domain['domain_id'],field_id=field_id).one()
    except:
        raise
        # TODO: better message
        abort(404)

def post_field(data):
    try:
        data = add_field.validate(data)
        schema = data.pop('schema', None)
        record = Field(**data)
        if schema:
            record.set_schema(schema, g.lang)
    except vno_err.ValidationErrorStack as es:
        # TODO: handle ValidationErrorStack here
        abort(400, str(es))

    try:
        db.session.add(record)
        db.session.flush()
    except exc.IntegrityError:
        db.session.rollback()
        abort(409)

    redirect_url = api_url('api.get_field', field_id=clean_uuid(record.field_id))
    return ({'location':redirect_url, 'field_id':clean_uuid(record.field_id)},
             201, [('Location',redirect_url)])

#TODO: validate field_type vs schema

def put_field(field_id, data):
    record = _get_field(field_id)
    # this is mostly to be safe, only the schema field is updated
    # on the record
    #def pop_members(data, state):
    #    for m in ['field_id', 'field_type', 'name', 'domain_id']:
    #        data.pop(m, None)
    #    return data

    try:
        data = edit_field.validate(data)
        schema = data.pop('schema', None)
        for k, v in data.items():
           setattr(record, k, v)
        if schema:
            record.set_schema(schema, g.lang)
    except vno_err.ValidationErrorStack as es:
        # TODO: work with validation here
        abort(400)

    db.session.flush()
    redirect_url = api_url('api.get_field', field_id=clean_uuid(record.field_id))
    return ({}, 200, [])

def delete_field(field_id):
    fields = Field.__table__
    field_id = clean_uuid(field_id)
    if field_id is not None:
        db.session.execute(fields.delete().where(
            (fields.c.domain_id==g.domain['domain_id'])&
            (fields.c.field_id==field_id)))
    return ({}, 200, [])

def field_resource(record):
    rv = {
        'self': api_url('api.get_field', field_id=clean_uuid(record.field_id)),
        'field_id': clean_uuid(record.field_id),
        'name': record.name,
        'field_type': record.field_type,
        'schema': record.get_schema(g.lang),
    }
    return rv

def get_field(field_id):
    try:
        record = Field.query.filter_by(domain_id=g.domain['domain_id'],
                                field_id=field_id).one()
    except orm_exc.NoResultFound as e:
        abort(404)
    return field_resource(record), 200, []

def get_fields():
    rv = {
        'self': api_url('api.get_fields'),
        'fields': [
            field_resource(rec) for rec in Field.query.filter_by(
             domain_id=g.domain['domain_id']).all()],
            #{'url': api_url('api.get_field', field_id=str(rec.field_id)),
            # 'name': rec.name} for rec in Field.query.filter_by(
            # domain_id=g.domain['domain_id']).all()],
    }
    return rv, 200, []
# \Fields
