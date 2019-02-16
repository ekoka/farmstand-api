from . import db

class Domain(db.Model):
    __tablename__ = 'domains'

    domain_id = db.Column(db.Integer, primary_key=True)
    owner_account_id = db.Column(None, db.ForeignKey(
        'accounts.account_id'), nullable=False)
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
    owner = db.relationship('Account', backref="owned_domains")


class DomainAccount(db.Model):
    __tablename__ = 'domain_accounts'

    domain_id = db.Column(None, db.ForeignKey(
        'domains.domain_id', ondelete='cascade'), primary_key=True)
    account_id = db.Column(None, db.ForeignKey(
        'accounts.account_id', ondelete='cascade'), primary_key=True)
    role = db.Column(db.Unicode, nullable=False, default='buyer')

    domain = db.relationship(Domain, backref='accounts')
    account = db.relationship('Account', backref='domains')
