from . import db
from uuid import uuid4
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.sql.expression import case, ClauseElement
from sqlalchemy.ext.compiler import compiles
from ..trigger import Trigger, TriggerProcedure
from ..view import view_mapper, create_view
from  sqlalchemy.types import TypeDecorator
#from sqlalchemy.events import DDLEvents
from sqlalchemy import event

class TSVector(TypeDecorator):
    impl = db.UnicodeText

@compiles(TSVector, 'postgresql')
def render_pgtsvector(element, compiler, **kw):
    return 'tsvector'

db.TSVector = TSVector

class CTE(ClauseElement):
    def __init__(self, queries, query):
        self.queries = queries
        self.query = query


@compiles(CTE, 'postgresql')
def with_clause(element, compiler, **kw):
    aliases =  ",".join(["{name} as ({query})".format(
        name=q, query=compiler.process(v)) 
        for n,q in element.queries.iteritems() if n and q
    ])
    return "with {aliases} {query}".format(
        aliases=aliases,
        query=compiler.process(element.query))

class ProductSchema(db.Model):
    __tablename__ = 'product_schema'

    product_schema_id = db.Column(
        None, db.ForeignKey('tenants.tenant_id'), primary_key=True)
    data = db.Column(db.JSONB, default=dict)

    tenant = db.relationship('Tenant', backref="product_schema")
    #tenant = db.relationship(
    #    'Tenant', backref="product_schema", 
    #    foreign_keys='[ProductSchema.product_schema_id]')

class Product(db.Model, db.TenantMixin):
    __tablename__ = 'products'

    product_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    available = db.Column(db.Boolean, default=False)
    visible = db.Column(db.Boolean, default=False)
    data = db.Column(db.JSONB, default=lambda: {})

class RelatedProduct(db.Model, db.TenantMixin):
    __tablename__ = 'related_products'
    
    left_id = db.Column(None)
    right_id = db.Column(None)

    __table_args__ = (
        db.ForeignKeyConstraint([left_id, 'tenant_id'], 
                                ['products.product_id', 'products.tenant_id']),
        db.ForeignKeyConstraint([right_id, 'tenant_id'], 
                                ['products.product_id', 'products.tenant_id']),
        db.CheckConstraint(left_id<right_id),
    )

class ProductSearch(db.TenantMixin, db.Model):
    __tablename__ = 'product_search'

    product_id = db.Column(None, primary_key=True)
    lang = db.Column(db.Unicode, primary_key=True)
    search = db.Column(db.TSVector)

    __table_args__ = (
        db.ForeignKeyConstraint([product_id, 'tenant_id'], 
                                ['products.product_id', 'products.tenant_id']),
    )

