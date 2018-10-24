from . import db

class Tenant(db.Model):
    __tablename__ = 'tenants'

    tenant_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode, unique=True)
    company_name = db.Column(db.Unicode)
    data = db.Column(db.JSONB)
    """
    {
        "company_name"
        "address1"
        "address2"
        "city"
        "state_province"
        "country"
        "zip_postal_code"
        "telephone"
        "website"
        "email"
    }
    """
    account_id = db.Column(None, db.ForeignKey('accounts.account_id'))

    account = db.relationship(
        'Account', backref=db.backref('tenant', uselist=False))
