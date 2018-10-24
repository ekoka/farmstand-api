from uuid import uuid4

from . import db

"""
Filters are a generic type used to categorize products. 
They can be organized in sets as well as hierarchically.
"""

class FilterSet(db.Model, db.TenantMixin):
    __tablename__ = 'filter_sets'

    filter_set_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    data = db.Column(db.JSONB, default=dict)

class Filter(db.Model, db.TenantMixin):

    __tablename__ = 'filters'
    
    filter_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    filter_set_id = db.Column(None)
    name = db.Column(db.Unicode)
    level = db.Column(db.Integer)
    parent_id = db.Column(None) 
    data = db.Column(db.JSONB, default=dict)
    """
        data: {
            label:{
                'en': '...',
                'fr': '...',
            }
        }
    """

    __table_args__ = (
        db.ForeignKeyConstraint([filter_set_id, 'tenant_id'], 
                                ['filter_sets.filter_set_id', 'filter_sets.tenant_id'],
                                'filters_filter_set_id_fkey'),
        db.ForeignKeyConstraint([parent_id, 'tenant_id'], 
                                ['filters.filter_id', 'filters.tenant_id'],
                                'filters_filter_id_fkey'),
    )

    parent = db.relationship(
        'Filter', backref='children',
        remote_side='[Filter.filter_id, Filter.tenant_id]')

    filter_set = db.relationship('FilterSet', backref='filters')


class ProductFilter(db.Model, db.TenantMixin):
    __tablename__ = 'products_filters'

    product_id = db.Column(None, primary_key=True)
    filter_id = db.Column(None, primary_key=True)

    __table_args__ = (
        db.ForeignKeyConstraint([filter_id, 'tenant_id'], 
                                ['filters.filter_id', 'filters.tenant_id'],
                                'products_filters_filter_id_fkey'),
        db.ForeignKeyConstraint([product_id, 'tenant_id'],
                                ['products.product_id', 'products.tenant_id'],
                                'products_filters_product_id_fkey'),
    )
