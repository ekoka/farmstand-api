from uuid import uuid4

from . import db

class Inquiry(db.Model, db.TenantMixin):
    __tablename__ = 'inquiries'

    inquiry_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    inquiry_contact = db.Column(db.JSONB, default=dict)
    status = db.Column(db.Unicode)
    dates = db.Column(db.JSONB, default=dict)
    data = db.Column(db.JSONB, default=dict)

    products = db.relationship('InquiryProduct')

class InquiryProduct(db.Model, db.TenantMixin):
    __tablename__ = 'inquiry_products'

    inquiry_id = db.Column(None, primary_key=True)
    product_id = db.Column(None, primary_key=True)
    data = db.Column(db.JSONB, default=dict)

    __table_args__ = (
        db.ForeignKeyConstraint(
            [inquiry_id, 'tenant_id'], 
            ['inquiries.inquiry_id', 'inquiries.tenant_id'],
            'inquiry_products_inquiry_id_fkey', ondelete='CASCADE',
        ),
        db.ForeignKeyConstraint(
            [product_id, 'tenant_id'], 
            ['products.product_id', 'products.tenant_id'],
            'inquiry_products_product_id_fkey', ondelete='CASCADE',
        ),
    )

