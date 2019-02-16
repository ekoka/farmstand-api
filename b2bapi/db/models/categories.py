from . import db

class Category(db.Model, db.DomainMixin):

    __tablename__ = 'categories'
    
    category_id = db.Column(db.UUID, primary_key=True)
    name = db.Column(db.Unicode)
    level = db.Column(db.Integer)
    parent_id = db.Column(None) 
    data = db.Column(db.JSONB)
    """
        data: {
            label:{
                'en': '...',
                'fr': '...',
            }
        }
    """

    __table_args__ = (
        db.ForeignKeyConstraint([parent_id, 'domain_id'], 
                                ['categories.category_id', 'categories.domain_id'],
                                'categories_category_id_fkey'),
    )

    parent = db.relationship(
        'Category', backref='children', 
        remote_side='[Category.category_id, Category.domain_id]')

class ProductCategory(db.Model, db.DomainMixin):
    __tablename__ = 'products_categories'

    product_id = db.Column(None, primary_key=True)
    category_id = db.Column(None, primary_key=True)

    __table_args__ = (
        db.ForeignKeyConstraint([category_id, 'domain_id'], 
                                ['categories.category_id', 'categories.domain_id'],
                                'products_categories_category_id_fkey'),
        db.ForeignKeyConstraint([product_id, 'domain_id'],
                                ['products.product_id', 'products.domain_id'],
                                'products_categories_product_id_fkey'),
    )
