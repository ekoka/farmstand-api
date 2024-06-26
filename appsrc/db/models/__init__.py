from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.types import TypeDecorator
import sqlalchemy.dialects.postgresql as pg
from ..pgjson import JSON, JSONB

db = SQLAlchemy()

class Integer(TypeDecorator):

    impl = db.Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, str):
            try:
                value = int(value)
            except:
                value = None
        return value

def populate(self, **data):
    for k,v in data.items():
        if hasattr(self, k):
            setattr(self, k, v)

db.Integer = Integer
db.Model.populate = populate
db.UUID = pg.UUID(as_uuid=True)
# overriding the more general JSON data types with more postgresql specific
db.pg = pg
db.JSON = JSON
db.JSONB = JSONB
#db.ARRAY = pg.ARRAY

class DomainMixin(object):

    @declared_attr
    def domain_id(self):
        return db.Column(None, db.ForeignKey(
            'domains.domain_id', ondelete='cascade'), primary_key=True)


db.DomainMixin = DomainMixin

from . import (
    billing,
    domains,
    products,
    groups,
    images,
    accounts,
    inquiries,
    #quotations,
    meta,
    security,
)
