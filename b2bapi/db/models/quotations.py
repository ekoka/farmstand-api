from uuid import uuid4
from datetime import datetime

from . import db

class Quotation(db.Model, db.DomainMixin):
    __tablename__ = 'quotations'

    quotation_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    status = db.Column(db.Unicode)
    post_date = db.Column(db.DateTime, default=datetime.utcnow)
    currency = db.Column(db.Unicode, nullable=False)
    terms = db.Column(db.Unicode)
    data = db.Column(db.JSONB, default=dict)

    products = db.relationship('QuotationProduct')

class QuotationEvent(db.Model, db.DomainMixin):
    __tablename__ = 'quotation_events'

    quotation_event_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    quotation_id = db.Column(None)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.Unicode, nullable=False)
    noted = db.Column(db.Boolean, default=False)
    """
    quotation open 
    quotation canceled
    comment added
    terms changed
    currency changed
    """
    __table_args__ = (
        db.ForeignKeyConstraint(
            [quotation_id, 'domain_id'],
            ['quotations.quotation_id', 'quotations.domain_id'],
            'quotation_events_quotation_id_fkey',
            ondelete='CASCADE',
        ),
    )

class QuotationProduct(db.Model, db.DomainMixin):
    __tablename__ = 'quotation_products'

    quotation_product_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    quotation_id = db.Column(None)
    product_id = db.Column(None)
    unit_price = db.Column(db.Numeric)
    unit_description = db.Column(db.Unicode)
    quantity = db.Column(db.Numeric)
    status = db.Column(db.Unicode) # open, canceled, approved
    data = db.Column(db.JSONB, default=dict)
    """
    {
        "amounts": {
            "requested_quantity": <quantity>,
            "subtotal": {"amount": <subtotal>, description: "", negative=false},
            "discount": {
                "type": "rate"|"fixed"|"percent", "value":25, "description":"", 
                "negative":true, "resulting_amount": <resulting_amount>
            },
            "taxes": {"type": "rate"|"fixed"|"percent", "value":14.49, 
                        "description":"TPS & TVQ", "negative"=true, 
                        "resulting_amount":<resulting_amount>
            },
        },
        
    }
    """

    __table_args__ = (
        db.UniqueConstraint(quotation_id, product_id), # ensure 1 product_id per quotation
        db.ForeignKeyConstraint(
            [quotation_id, 'domain_id'], 
            ['quotations.quotation_id', 'quotations.domain_id'],
            'quotation_products_quotation_id_fkey', ondelete='CASCADE',
        ),
        db.ForeignKeyConstraint(
            [product_id, 'domain_id'], 
            ['products.product_id', 'products.domain_id'],
            'quotation_products_product_id_fkey', ondelete='CASCADE',
        ),
    )

class QuotationProductEvent(db.Model, db.DomainMixin):
    __tablename__ = 'quotation_product_events'

    quotation_product_event_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    quotation_product_id = db.Column(None)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.Unicode, nullable=False)
    noted = db.Column(db.Boolean, default=False)
    """
        "added"
        "removed", 
        "approved", 
        "price_set",
        "price_changed",
        "quantity_set",
        "quantity_changed",
        "discount_set",
        "discount_changed",
        "discount_removed",
        "shipping_charges_set",
        "shipping_charges_changed",
        "shipping_charges_removed",
        "taxes_set",
        "taxes_changed",
        "taxes_removed",
        ... taxes, total,
    """
    __table_args__ = (
        db.ForeignKeyConstraint(
            [quotation_product_id, 'domain_id'], 
            ['quotation_products.quotation_product_id', 
             'quotation_products.domain_id'],
            'quotation_product_events_quotation_product_id_fkey', 
            ondelete='CASCADE',
        ),
    )

class QuotationProductComment(db.Model, db.DomainMixin):
    __tablename__ = 'quotation_product_comments'

    comment_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    quotation_product_id = db.Column(None)
    comment = db.Column(db.Unicode, nullable=False)
    account_id = db.Column(None, db.ForeignKey(
        'accounts.account_id', ondelete='cascade'))
    post_date = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.JSONB, default=dict)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [quotation_product_id, 'domain_id'], 
            ['quotation_products.quotation_product_id', 
             'quotation_products.domain_id'],
            'quotation_product_comments_quotation_product_id_fkey', 
            ondelete='CASCADE',
        ),
    )
