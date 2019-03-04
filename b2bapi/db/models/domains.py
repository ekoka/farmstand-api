from . import db

class Domain(db.Billable):
    __tablename__ = 'domains'

    domain_id = db.Column(None, db.ForeignKey('billables.billable_id'),
                          primary_key=True)
    name = db.Column(db.Unicode, unique=True)
    company_name = db.Column(db.Unicode)
    creation_date = db.Column(db.DateTime)
    data = db.Column(db.JSONB)

    localized_fields = ['label', 'description']

    __mapper_args__ = dict(polymorphic_identity='domains')


class DomainAccount(db.Model):
    __tablename__ = 'domain_accounts'

    domain_id = db.Column(None, db.ForeignKey(
        'domains.domain_id', ondelete='cascade'), primary_key=True)
    account_id = db.Column(None, db.ForeignKey(
        'accounts.account_id', ondelete='cascade'), primary_key=True)
    role = db.Column(db.Unicode, nullable=False, default='buyer')

    domain = db.relationship(Domain, backref='accounts')
    account = db.relationship('Account', backref='domains')
