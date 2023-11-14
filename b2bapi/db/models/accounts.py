from . import db
from uuid import uuid4
import bcrypt
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime as dtm
from ...utils.password import match_passwords, encrypt_password

"""
- Each user has a single account.
"""
class Account(db.Model):
    __tablename__ = 'accounts'
    account_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    stripe_customer_id = db.Column(db.Unicode, unique=True, nullable=False)
    name = db.Column(db.Unicode)
    email = db.Column(db.Unicode, unique=True)
    _password = db.Column('password', db.Unicode)
    lang = db.Column(db.Unicode, default='en')
    data = db.Column(db.JSONB, default=dict)
    id_token = db.Column(db.Unicode, unique=True, nullable=True)
    confirmed = db.Column(db.Boolean, default=False)

    # these fields should be localized in the `data` json
    localized_fields = ['organization', 'role', 'bio', 'location',]

    @property
    def primary_email(self):
        for e in self.emails:
            if e.primary and e.verified:
                return e

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = encrypt_password(password)

    def authenticate(self, password):
        # password must be an unicode object
        try:
            return match_passwords(self.password, password)
        except AttributeError:
            return False

    def authorize(self, domain, action, **kw):
        if action is True: # basic authz
            return self.account_id==domain.owner_account_id

        if callable(action):
            return action(domain, self)

    def authorization(fnc, roles):
        @functools.wraps(fnc)
        def wrapper(*a, **kw):
            authorized = app.config.get('DEV_MODE', False)
            # if a resource must go through authorization a current_account should
            # be present in g.
            acc = g.current_account
            authorized = acc.authorize(g.domain, roles, **kw) or authorized

class PaymentSource(db.Model):
    __tablename__ = 'payment_sources'
    source_id = db.Column(db.Unicode, primary_key=True)
    account_id = db.Column(None, db.ForeignKey('accounts.account_id'))
    data = db.Column(db.JSONB, default=dict)
    default_source = db.Column(db.Boolean, default=False)

    account = db.relationship(Account, backref='payment_sources')


class AccountAccessKey(db.Model):
    __tablename__ = 'account_access_keys'

    key = db.Column(db.Unicode, primary_key=True)
    account_id = db.Column(None, db.ForeignKey('accounts.account_id'))
    secret = db.Column(db.Unicode)
    creation_timestamp = db.Column(db.DateTime, default=dtm.utcnow)
    fail_count = db.Column(db.Integer, default=0)
    fail_timestamp = db.Column(db.DateTime)

    account = db.relationship(
        'Account', backref=db.backref('access_key', uselist=False))


"""
- An account can have multiple alternate emails.
- Each account has one primary email.
- An email is unique and only belongs to one account.
"""
class AccountEmail(db.Model):
    __tablename__ = 'account_emails'
    account_email_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    account_id = db.Column(None, db.ForeignKey('accounts.account_id'))
    email = db.Column(db.Unicode, unique=True, nullable=False)
    verified = db.Column(db.Boolean)
    primary = db.Column(db.Boolean, default=False)
    login = db.Column(db.Boolean, default=False) # make sure to warn users

    account = db.relationship(
        'Account', backref=db.backref("emails", order_by='AccountEmail.primary'))


class Invite(db.Model, db.DomainMixin):
    """
    A merchant can invite users to access their catalog.
    """
    __tablename__ = 'invites'

    email = db.Column(db.Unicode, primary_key=True)
    status = db.Column(db.Unicode)
    #request_date = db.Column(db.DateTime)
    #accept_date = db.Column(db.DateTime)
    #status_change = db.Column(db.DateTime)


#class User(db.Model, db.DomainMixin):
#    """
#    Table of accounts that were granted access to domain.
#    """
#    __tablename__ = 'users'
#    account_id = db.Column(
#        None, db.ForeignKey('accounts.account_id'), primary_key=True)
#
#    domain = db.relationship('Domain', backref='invites')
#


class Signin(db.Model):
    __tablename__='signins'
    signin_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    email = db.Column(db.Unicode, unique=True)
    passcode = db.Column('passcode', db.Unicode, nullable=True)
    passcode_timestamp = db.Column(db.DateTime)
    sent = db.Column(db.Boolean, default=False)
    fail_count = db.Column(db.Integer)

    #def authenticate(self, passcode):
    #    if not self.passcode==passcode:
    #        self.failure += 1
    #        return False
    #    self.failure = 0
    #    return True
    #    # TODO:  update `last_successful` to dtm.now()
    #

    #def clear_passcode(self):
    #    self.passcode = None

    #def get_token(self, token_type='access_token', status='active'):
    #    for i,t in enumerate(self.meta.get('tokens', [])):
    #        if t.get('type')==token_type and t.get('status')==status:
    #            return t

    #@classmethod
    #def generate_token(cls, **kw):
    #    token_type = kw.pop('token_type')
    #    key = randomstr(32)
    #    token = f'{token_type}_{key}'
    #    status = kw.pop('status', 'pending')
    #    token = {
    #        'type': token_type,
    #        'status': status,
    #        'token': token,
    #        'timestamp': dtm.datetime.utcnow().isoformat(),
    #        **kw,
    #    }
    #    return token

    #def set_token(self, **kw):
    #    token = self.generate_token(**kw)
    #    self.meta.setdefault('tokens', []).append(token)
    #    return token

    #def remove_tokens(self, token_types=None):
    #    if token_types is None: # clear all tokens
    #        self.meta['tokens'][:] = []
    #        return
    #    try:
    #        self.meta['tokens'][:] = (t for t in self.meta['tokens']
    #                                  if t['type'] not in token_types)
    #    except (KeyError, IndexError) as e:
    #        pass



# TODO: ENABLE class UserView(db.Model): __abstract__=True
# TODO: ENABLE view_mapper('users_view', User.__table__.select(), db.metadata, UserView,
# TODO: ENABLE             db.Column('user_id', db.Integer, db.ForeignKey(
# TODO: ENABLE                 'users.user_id'), primary_key=True))
