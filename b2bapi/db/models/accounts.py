from . import db
from uuid import uuid4

"""
- Each user has a single account.
"""
class Account(db.Model):
    __tablename__ = 'accounts'
    account_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    first_name = db.Column(db.Unicode)
    last_name = db.Column(db.Unicode)
    email = db.Column(db.Unicode, unique=True)
    lang = db.Column(db.Unicode, default='en')
    data = db.Column(db.JSONB)

class AccountAccessKey(db.Model):
    __tablename__ = 'account_access_keys'

    key = db.Column(db.Unicode, primary_key=True)
    account_id = db.Column(
        None, db.ForeignKey('accounts.account_id'), unique=True, nullable=False)
    secret = db.Column(db.Unicode)
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

"""
- Each email can be linked to multiple profiles.
"""
class Profile(db.Model):

    __tablename__ = 'profiles'

    profile_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    account_email_id = db.Column(
        None, db.ForeignKey('account_emails.account_email_id'), nullable=False)
    profile_name = db.Column(db.Unicode)
    first_name = db.Column(db.Unicode)
    middle_name = db.Column(db.Unicode)
    last_name = db.Column(db.Unicode)
    title = db.Column(db.Unicode) # Mr, Mrs, Dr, Pr
    company = db.Column(db.Unicode)
    role = db.Column(db.Unicode) # CEO, CTO
    contact = db.Column(db.JSONB)
    """
    phone:
        mobile:
        work:
    address1
    address2
    city
    state_province
    zip_postal_code
    country
    """
    preferred_languages = db.Column(db.JSONB)
    data = db.Column(db.JSONB)
    account_id = db.Column(None, db.ForeignKey('accounts.account_id'))
    # is primary profile for this account
    is_primary = db.Column(db.Boolean, default=False) 

    # relationships
    email = db.relationship('AccountEmail', backref='profiles')


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
#- An account could administer multiple tenants to some capacity.
#- Only one role per account per tenant.
#"""
#class AccountRoles(db.Model, db.TenantMixin):
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
#class AccessRequest(db.Model, db.TenantMixin):
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
#    tenant = db.relationship('Tenant', backref='access_requests')
#
#
#"""
#- A merchant can invite a user to access their catalog.
#"""
#class InviteRequest(db.Model, db.TenantMixin):
#
#    __tablename__ = 'invite_requests'
#
#    email = db.Column(db.Unicode, primary_key=True)
#    status = db.Column(db.Unicode)
#    request_date = db.Column(db.DateTime)
#    accept_date = db.Column(db.DateTime)
#    status_change = db.Column(db.DateTime)
#
#    tenant = db.relationship('Tenant', backref='invites')
#
#
#"""
#- A merchant can have many clients. Some of whom might not have an account.
#- A client with an account that has accepted a merchant's invite becomes
#linked.
#- The email field cannot be modified in a linked address.
#"""
#class Client(db.Model, db.TenantMixin):
#
#    __tablename__ = 'clients'
#
#    client_id = db.Column(db.UUID, primary_key=True)
#    email = db.Column(db.Unicode, unique=True, nullable=True)
#    linked = db.Column(db.Boolean) # linked to an Account (via email)
#    data = db.Column(db.JSONB)
#
#    tenant = db.relationship('Tenant', backref='clients')
#    # TODO: create a relationship linking account_email and client
#    # based on 'AccountEmail.email==Client.email'
#    account_email = db.relationship(
#        'AccountEmail', backref='client_profiles', 
#        primaryjoin='(AccountEmail.email==Client.email)&\
#        (AccountEmail.verified & Client.linked)')
#
#
