from . import db
from uuid import uuid4
from datetime import datetime as dtm

class Domain(db.Billable):
    __tablename__ = 'domains'

    domain_id = db.Column(None, db.ForeignKey('billables.billable_id'),
                          primary_key=True)
    name = db.Column(db.Unicode, unique=True)
    creation_date = db.Column(db.DateTime, default=dtm.utcnow)
    data = db.Column(db.JSONB, default=dict)
    meta = db.Column(db.JSONB, default=dict)
    # see additional fields in Billable model

    localized_fields = ['label', 'description']

    __mapper_args__ = dict(polymorphic_identity='domains')

    @staticmethod
    def default_meta():
        return {
            'privacy': 'private',
            'access_approval': 'explicit',
            'languages': ['en'],
        }

    admin_join = "(DomainAccount.role=='admin') &\
        (DomainAccount.account_id==Account.account_id)"

    admins = db.relationship(
        'Account', secondary='domain_accounts', viewonly=True,
        secondaryjoin=admin_join, backref='admin_domains')

class DomainAccount(db.Model, db.DomainMixin):
    __tablename__ = 'domain_accounts'

    account_id = db.Column(None, db.ForeignKey(
        'accounts.account_id', ondelete='cascade'), primary_key=True)
    active = db.Column(db.Boolean, default=False)
    role = db.Column(db.Unicode, nullable=False, default='user')

    domain = db.relationship(Domain, backref='accounts')
    account = db.relationship('Account', backref='domains')

class DomainAccessRequest(db.Model):
    """
    A user can request access to a merchant's catalog.
    """
    __tablename__ = 'domain_access_requests'
    access_request_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    account_id = db.Column(
        None, db.ForeignKey('accounts.account_id'), nullable=False)
    domain_id = db.Column(
        None, db.ForeignKey('domains.domain_id'), nullable=False)
    creation_date = db.Column(db.DateTime, default=dtm.utcnow)
    status = db.Column(db.Unicode)
    data = db.Column(db.JSONB, default=dict)

    account = db.relationship('Account', backref="access_requests")
    domain = db.relationship('Domain', backref="access_requets")
