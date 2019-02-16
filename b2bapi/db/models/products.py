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

class ProductSchema(db.Model, db.DomainMixin):
    __tablename__ = 'product_schema'

    product_schema_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    data = db.Column(db.JSONB, default=dict)

class Product(db.Model, db.DomainMixin):
    __tablename__ = 'products'

    product_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    visible = db.Column(db.Boolean, default=False)
    # TODO: fields to add:  
    #    logs: date_added, date_updated, updated_by
    data = db.Column(db.JSONB, default=dict)
    """
    {
        "fields": [
            {"field": <field>, "visible": <bool>, "searchable": <bool>}, 
            ... 
        ]
    }
    """
    product_family_id = db.Column(None, nullable=True)

    __table_args__ = (
        db.ForeignKeyConstraint([product_family_id, 'domain_id'], 
                                ['product_families.product_family_id', 
                                 'product_families.domain_id'],
                               'products_product_family_id_fkey'),
    )

class ProductFamily(db.Model, db.DomainMixin):
    """
    The idea behind product families is that some products might just be
    different versions of one another. The differing features being such
    attributes as size, color, etc. 
    Product families enable to associate them in a grouping.
    """
    __tablename__ = 'product_families'

    product_family_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    main_product_id = db.Column(None)

    __table_args__ = (
        db.ForeignKeyConstraint([main_product_id, 'domain_id'],
                                ['products.product_id', 'products.domain_id'],
                               'product_families_main_product_id_fkey'),
    )

class RelatedProduct(db.Model, db.DomainMixin):
    """
    Related products are products that have some common traits, even if not
    from the same family. e.g. Gummy bear and gummy worms aren't the same
    products, but someone interested in one is likely to also be interested
    by the other.
    """
    __tablename__ = 'related_products'
    
    left_id = db.Column(None)
    right_id = db.Column(None)

    __table_args__ = (
        db.ForeignKeyConstraint([left_id, 'domain_id'], 
                                ['products.product_id', 'products.domain_id']),
        db.ForeignKeyConstraint([right_id, 'domain_id'], 
                                ['products.product_id', 'products.domain_id']),
        db.CheckConstraint(left_id<right_id),
    )

class ProductSearch(db.Model, db.DomainMixin):
    __tablename__ = 'product_search'

    product_id = db.Column(None, primary_key=True)
    lang = db.Column(db.Unicode, primary_key=True)
    search = db.Column(db.TSVector)

    __table_args__ = (
        db.ForeignKeyConstraint([product_id, 'domain_id'], 
                                ['products.product_id', 'products.domain_id']),
    )
