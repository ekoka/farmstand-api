from vino import errors as vno_err

from ..db import db
from ..db.models.meta import Field
from ..utils.uuid import clean_uuid
from .validation.meta import add_field, edit_field
from . import errors as err

def get_field(field_id, domain_id):
    # service
    field_id = clean_uuid(field_id)
    notfound = lambda: err.NotFound(f'Field {field_id} not found')
    try:
        if field_id is None:
            raise notfound()
        return Field.query.filter_by(domain_id=domain_id, field_id=field_id).one()
    except:
        raise notfound()

def create_field(domain_id, data, lang):
    # service
    try:
        data = add_field.validate(data)
        schema = data.pop('schema', None)
        field = Field(**data)
        if schema:
            field.set_schema(schema, lang)
    except vno_err.ValidationErrorStack as es:
        db.session.rollback()
        raise err.FormatError(f'Could not create field: {str(es)}')
    try:
        db.session.add(field)
        db.session.flush()
    except exc.IntegrityError:
        db.session.rollback()
        raise err.Conflict(f'Could not add field')
    return field

#TODO: validate field_type vs schema
def update_field(field_id, domain_id, data, lang):
    # service
    field = get_field(field_id, domain_id)
    # This is mostly to be safe, only the schema field is updated on the record
    #def pop_members(data, state):
    #    for m in ['field_id', 'field_type', 'name', 'domain_id']:
    #        data.pop(m, None)
    #    return data
    try:
        data = edit_field.validate(data)
        schema = data.pop('schema', None)
        for k, v in data.items():
           setattr(field, k, v)
        if schema:
            field.set_schema(schema, lang)
        db.session.flush()
    except vno_err.ValidationErrorStack as es:
        # TODO: work with validation here
        db.session.rollback()
        raise err.FormatError(f'Could not update field {field_id}')
    return field

def delete_field(field_id, domain_id):
    # service
    fields_tbl = Field.__table__
    field_id = clean_uuid(field_id)
    try:
        db.session.execute(fields_tbl.delete().where(
            (fields_tbl.c.domain_id==domain_id) &
            (fields_tbl.c.field_id==field_id)))
    except:
        db.session.rollback()

def get_fields(domain_id):
    # service
    return Field.query.filter_by(domain_id=domain_id).all()
