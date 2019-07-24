from uuid import uuid4
from datetime import datetime

from . import db

class Inquiry(db.Model, db.DomainMixin):
    __tablename__ = 'inquiries'

    inquiry_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    status = db.Column(db.Unicode, default='open')
    post_date = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.Column(db.Unicode)
    account_id = db.Column(None, db.ForeignKey(
        'accounts.account_id', ondelete='SET NULL', onupdate='CASCADE'), 
        nullable=True)
    data = db.Column(db.JSONB, default=dict)
    """
    - shipping
    - billing
    - contact information
    messages : [
        {'account_id', 'timestamp', 'comment'},
    ],
    - language of submission
    - email status
    """

    products = db.relationship('InquiryProduct')

class InquiryProduct(db.Model, db.DomainMixin):
    __tablename__ = 'inquiry_products'

    inquiry_product_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    inquiry_id = db.Column(None)
    product_id = db.Column(None)
    quantity = db.Column(db.Unicode)
    status = db.Column(db.Unicode, default='added') # removed
    data = db.Column(db.JSONB, default=dict)
    """
    {
        messages : [
            {'account_id', 'timestamp', 'comment'},
        ],
    }
    """

    __table_args__ = (
        db.UniqueConstraint(inquiry_id, product_id), # ensure 1 product_id per inquiry
        db.ForeignKeyConstraint(
            [inquiry_id, 'domain_id'], 
            ['inquiries.inquiry_id', 'inquiries.domain_id'],
            'inquiry_products_inquiry_id_fkey', ondelete='CASCADE',
        ),
        db.ForeignKeyConstraint(
            [product_id, 'domain_id'], 
            ['products.product_id', 'products.domain_id'],
            'inquiry_products_product_id_fkey', ondelete='CASCADE',
        ),
    )
