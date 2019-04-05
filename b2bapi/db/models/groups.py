from uuid import uuid4

from . import db

"""
Groups are a generic type used to categorize products. 
They can be organized in sets as well as hierarchically.
"""

class Group(db.Model, db.DomainMixin):
    __tablename__ = 'groups'

    group_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    active = db.Column(db.Boolean, default=False)
    multichoice = db.Column(db.Boolean, default=False)
    data = db.Column(db.JSONB, default=dict)

class GroupOption(db.Model, db.DomainMixin):

    __tablename__ = 'group_options'
    
    group_option_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    group_id = db.Column(None)
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
            [group_id, 'domain_id'], 
            ['groups.group_id', 'groups.domain_id'],
            'groups_group_id_fkey', ondelete='cascade'),
        db.ForeignKeyConstraint(
            [parent_id, 'domain_id'], 
            ['group_options.group_option_id', 'group_options.domain_id'],
            'group_options_group_option_id_fkey', ondelete='cascade'),
    )

    parent = db.relationship(
        'GroupOption', backref='children',
        remote_side='[GroupOption.group_option_id, GroupOption.domain_id]', 
        viewonly=True)

    group = db.relationship('Group', backref=db.backref(
        'options', order_by='GroupOption.position'))

    primaryjoin=("(GroupOption.group_option_id==foreign("
                 "ProductGroupOption.group_option_id))&(GroupOption.domain_id=="
                 "foreign(ProductGroupOption.domain_id))") 
    secondaryjoin=("(Product.product_id==foreign(ProductGroupOption.product_id))&"
                 "(Product.domain_id==ProductGroupOption.domain_id)") 
    products = db.relationship(
        'Product', secondary="products_group_options", primaryjoin=primaryjoin, 
        secondaryjoin=secondaryjoin, backref="group_options")


class ProductGroupOption(db.Model, db.DomainMixin):
    __tablename__ = 'products_group_options'

    product_id = db.Column(None, primary_key=True)
    group_option_id = db.Column(None, primary_key=True)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [group_option_id, 'domain_id'], 
            ['group_options.group_option_id', 'group_options.domain_id'],
            'products_group_options_group_option_id_fkey', ondelete='cascade',
        ), 
        db.ForeignKeyConstraint(
            [product_id, 'domain_id'],
            ['products.product_id', 'products.domain_id'],
            'products_group_options_product_id_fkey', ondelete='cascade',
        ),
    )
