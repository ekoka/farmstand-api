from uuid import uuid4

from . import db

"""
Filters are a generic type used to categorize products. 
They can be organized in sets as well as hierarchically.
"""

class Filter(db.Model, db.TenantMixin):
    __tablename__ = 'filters'

    filter_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    active = db.Column(db.Boolean, default=False)
    multichoice = db.Column(db.Boolean, default=False)
    data = db.Column(db.JSONB, default=dict)

class FilterOption(db.Model, db.TenantMixin):

    __tablename__ = 'filter_options'
    
    filter_option_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    filter_id = db.Column(None)
    position = db.Column(db.Integer, default=0)
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
        db.ForeignKeyConstraint(
            [filter_id, 'tenant_id'], 
            ['filters.filter_id', 'filters.tenant_id'],
            'filters_filter_id_fkey', ondelete='cascade'),
        db.ForeignKeyConstraint(
            [parent_id, 'tenant_id'], 
            ['filter_options.filter_option_id', 'filter_options.tenant_id'],
            'filter_options_filter_option_id_fkey', ondelete='cascade'),
    )

    parent = db.relationship(
        'FilterOption', backref='children',
        remote_side='[FilterOption.filter_option_id, FilterOption.tenant_id]', 
        viewonly=True)

    filter = db.relationship('Filter', backref=db.backref(
        'options', order_by='FilterOption.position'))

    primaryjoin=("(FilterOption.filter_option_id==foreign("
                 "ProductFilterOption.filter_option_id))&(FilterOption.tenant_id=="
                 "foreign(ProductFilterOption.tenant_id))") 
    secondaryjoin=("(Product.product_id==foreign(ProductFilterOption.product_id))&"
                 "(Product.tenant_id==ProductFilterOption.tenant_id)") 
    products = db.relationship(
        'Product', secondary="products_filter_options", primaryjoin=primaryjoin, 
        secondaryjoin=secondaryjoin, backref="filter_options")


class ProductFilterOption(db.Model, db.TenantMixin):
    __tablename__ = 'products_filter_options'

    product_id = db.Column(None, primary_key=True)
    filter_option_id = db.Column(None, primary_key=True)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [filter_option_id, 'tenant_id'], 
            ['filter_options.filter_option_id', 'filter_options.tenant_id'],
            'products_filter_options_filter_option_id_fkey', ondelete='cascade',
        ), 
        db.ForeignKeyConstraint(
            [product_id, 'tenant_id'],
            ['products.product_id', 'products.tenant_id'],
            'products_filter_options_product_id_fkey', ondelete='cascade',
        ),
    )
