from . import db
from uuid import uuid4
import bcrypt
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime as dtm
from b2bapi.utils.password import match_passwords, encrypt_password

"""
- Each user has a single account.
"""
class Account(db.Model):
    __tablename__ = 'accounts'
    account_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    stripe_customer_id = db.Column(db.Unicode, unique=True, nullable=False)
    first_name = db.Column(db.Unicode)
    last_name = db.Column(db.Unicode)
    email = db.Column(db.Unicode, unique=True)
    _password = db.Column('password', db.Unicode)
    lang = db.Column(db.Unicode, default='en')
    data = db.Column(db.JSONB, default=dict)
    confirmed = db.Column(db.Boolean, default=False)

    # these fields should be localized in the `data` json 
    localized_fields = ['company', 'role', 'summary', 'address', 'city',
                        'state_province', 'country']

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


class AccessRequest(db.Model, db.DomainMixin):
    """
    User can request access to a merchant's catalog.
    """
    __tablename__ = 'access_requests'
    account_id = db.Column(
        None, db.ForeignKey('accounts.account_id'), primary_key=True)
    status = db.Column(db.Unicode)
    #request_time = db.Column(db.DateTime)
    #role = db.Column(db.Unicode, default="user")

    #__table_args__ = (
    #    db.UniqueConstraint('domain_id', 'account_id'),
    #)

class User(db.Model, db.DomainMixin):
    """
    Table of accounts that were granted access to domain.
    """
    __tablename__ = 'users'
    account_id = db.Column(
        None, db.ForeignKey('accounts.account_id'), primary_key=True)

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




#
#"""
#- Each email can be linked to multiple profiles.
#"""
#class Profile(db.Model):
#
#    __tablename__ = 'profiles'
#
#    profile_id = db.Column(db.UUID, primary_key=True, default=uuid4)
#    account_email_id = db.Column(
#        None, db.ForeignKey('account_emails.account_email_id'), nullable=False)
#    profile_name = db.Column(db.Unicode)
#    first_name = db.Column(db.Unicode)
#    middle_name = db.Column(db.Unicode)
#    last_name = db.Column(db.Unicode)
#    title = db.Column(db.Unicode) # Mr, Mrs, Dr, Pr
#    company = db.Column(db.Unicode)
#    role = db.Column(db.Unicode) # CEO, CTO
#    contact = db.Column(db.JSONB, default=dict)
#    """
#    phone:
#        mobile:
#        work:
#    address1
#    address2
#    city
#    state_province
#    zip_postal_code
#    country
#    """
#    preferred_languages = db.Column(db.JSONB, default=dict)
#    data = db.Column(db.JSONB, default=dict)
#    account_id = db.Column(None, db.ForeignKey('accounts.account_id'))
#    # is primary profile for this account
#    is_primary = db.Column(db.Boolean, default=False) 
#
#    # relationships
#    email = db.relationship('AccountEmail', backref='profiles')


#class AccountUnverifiedEmail(db.Model):
#    __tablename__ = 'account_unverified_emails'
#
#    account_email_id = db.Column(db.UUID, primary_key=True)
#    account_id = db.Column(None, db.ForeignKey('accounts.account_id'))
#    email = db.Column(db.Unicode, unique=True, nullable=False)
#    status = db.Column(db.Unicode, default='pending')
#    email_sent = db.Column(db.DateTime)
#
#    account = db.relationship(
#        'Account', backref=db.backref("unverified_emails"))
#
#
#"""
#- An account could administer multiple domains to some capacity.
#- Only one role per account per domain.
#"""
#class AccountRoles(db.Model, db.DomainMixin):
#
#    __tablename__ = 'account_roles'
#
#    account_id = db.Column(
#        None, db.ForeignKey('accounts.account_id'), primary_key=True)
#    role = db.Column(db.Unicode)
#    """
#        admin
#        sales manager
#        sales rep
#    """
#
#
#"""
#- A user can request access to a merchant's catalog.
#"""
#class AccessRequest(db.Model, db.DomainMixin):
#
#    __tablename__ = 'access_requests'
#
#    account_email_id = db.Column(
#        None, db.ForeignKey('account_emails.account_email_id'),
#        primary_key=True)
#    status = db.Column(db.Unicode) # pending, accept, reject
#    request_date = db.Column(db.DateTime)
#    accept_date = db.Column(db.DateTime)
#    status_change = db.Column(db.DateTime)
#
#    account_email = db.relationship('AccountEmail', backref='access_requests')
#    domain = db.relationship('Domain', backref='access_requests')
#
#
#"""
#- A merchant can have many clients. Some of whom might not have an account.
#- A client with an account that has accepted a merchant's invite becomes
#linked.
#- The email field cannot be modified in a linked address.
#"""
#class Client(db.Model, db.DomainMixin):
#
#    __tablename__ = 'clients'
#
#    client_id = db.Column(db.UUID, primary_key=True)
#    email = db.Column(db.Unicode, unique=True, nullable=True)
#    linked = db.Column(db.Boolean) # linked to an Account (via email)
#    data = db.Column(db.JSONB, default=dict)
#
#    domain = db.relationship('Domain', backref='clients')
#    # TODO: create a relationship linking account_email and client
#    # based on 'AccountEmail.email==Client.email'
#    account_email = db.relationship(
#        'AccountEmail', backref='client_profiles', 
#        primaryjoin='(AccountEmail.email==Client.email)&\
#        (AccountEmail.verified & Client.linked)')
#
#
