from uuid import uuid4

from . import db

"""
Filters are a generic type used to categorize products. 
They can be organized in sets as well as hierarchically.
"""

class Filter(db.Model, db.DomainMixin):
    __tablename__ = 'filters'

    filter_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    active = db.Column(db.Boolean, default=False)
    multichoice = db.Column(db.Boolean, default=False)
    data = db.Column(db.JSONB, default=dict)

class FilterOption(db.Model, db.DomainMixin):

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
            [filter_id, 'domain_id'], 
            ['filters.filter_id', 'filters.domain_id'],
            'filters_filter_id_fkey', ondelete='cascade'),
        db.ForeignKeyConstraint(
            [parent_id, 'domain_id'], 
            ['filter_options.filter_option_id', 'filter_options.domain_id'],
            'filter_options_filter_option_id_fkey', ondelete='cascade'),
    )

    parent = db.relationship(
        'FilterOption', backref='children',
        remote_side='[FilterOption.filter_option_id, FilterOption.domain_id]', 
        viewonly=True)

    filter = db.relationship('Filter', backref=db.backref(
        'options', order_by='FilterOption.position'))

    primaryjoin=("(FilterOption.filter_option_id==foreign("
                 "ProductFilterOption.filter_option_id))&(FilterOption.domain_id=="
                 "foreign(ProductFilterOption.domain_id))") 
    secondaryjoin=("(Product.product_id==foreign(ProductFilterOption.product_id))&"
                 "(Product.domain_id==ProductFilterOption.domain_id)") 
    products = db.relationship(
        'Product', secondary="products_filter_options", primaryjoin=primaryjoin, 
        secondaryjoin=secondaryjoin, backref="filter_options")


class ProductFilterOption(db.Model, db.DomainMixin):
    __tablename__ = 'products_filter_options'

    product_id = db.Column(None, primary_key=True)
    filter_option_id = db.Column(None, primary_key=True)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [filter_option_id, 'domain_id'], 
            ['filter_options.filter_option_id', 'filter_options.domain_id'],
            'products_filter_options_filter_option_id_fkey', ondelete='cascade',
        ), 
        db.ForeignKeyConstraint(
            [product_id, 'domain_id'],
            ['products.product_id', 'products.domain_id'],
            'products_filter_options_product_id_fkey', ondelete='cascade',
        ),
    )
