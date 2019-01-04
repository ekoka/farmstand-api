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

class TenantAccount(db.Model):
    __tablename__ = 'tenant_accounts'

    tenant_id = db.Column(None, db.ForeignKey(
        'tenants.tenant_id', ondelete='cascade'), primary_key=True)
    account_id = db.Column(None, db.ForeignKey(
        'accounts.account_id', ondelete='cascade'), primary_key=True)
    role = db.Column(db.Unicode, nullable=False, default='buyer')

    tenant = db.relationship(Tenant, backref='accounts')
    account = db.relationship('Account', backref='tenants')
