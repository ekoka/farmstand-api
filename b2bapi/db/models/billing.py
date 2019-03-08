from . import db
from uuid import uuid4
from datetime import datetime as dtm, timedelta

class Plan(db.Model):
    __tablename__ = 'plans'

    # synced with stripe's id
    plan_id = db.Column(db.Unicode, primary_key=True) 
    # allows to filter a type of plan. Mostly useful for listing different pricing 
    # for the same type of plans e.g. "catalog".
    plan_type = db.Column(db.Unicode)
    # stripe data
    data = db.Column(db.JSONB, default=dict)
    localized_fields = ['label', 'options']

class BillingError(Exception):
    pass

class Billable(db.Model):
    __tablename__ = 'billables'
    billable_id = db.Column(db.Integer, primary_key=True)
    # synced with stripe's plan id
    plan_id = db.Column(None, db.ForeignKey('plans.plan_id'))     
    subscription_id = db.Column(db.Unicode, unique=True, nullable=True)
    subscription_data = db.Column(db.JSONB, default=dict)
    owner_account_id = db.Column(None, db.ForeignKey(
        'accounts.account_id', ondelete='restrict'), nullable=False)
    # discriminator property (e.g. `domains`)
    relation = db.Column(db.Unicode)
    active = db.Column(db.Boolean)
    log = db.Column(db.JSONB, default=dict)
    """
    {
        activation_history: [],
        deactivation_history: [],
    }
    """
    # discriminator property
    __mapper_args__ = dict(polymorphic_on=relation)

    plan = db.relation(Plan, backref='billables')
    owner = db.relationship('Account', backref="billables")

db.Billable = Billable
    
class StripeCharge(db.Model):
    __tablename__='stripe_charges'

    charge_id = db.Column(db.Unicode, primary_key=True)
    account_id = db.Column(None, db.ForeignKey(
        'accounts.account_id', ondelete='restrict'))
    amount = db.Column(db.Integer, nullable=False, default=0) # alias to total
    currency = db.Column(db.Unicode)
    currency_recorded_usd_exchange_rate = db.Column(db.Numeric(
        precision=10, scale=7))
    created = db.Column(db.DateTime)
    #total = Column(Integer, nullable=False, default=0)
    taxes = db.Column(db.Integer, nullable=False, default=0)
    taxes_details = db.Column(db.JSONB, default=dict)
    card_last4 = db.Column(db.Unicode)
    card_brand = db.Column(db.Unicode)


class StripeRefund(db.Model):
    __tablename__='stripe_refunds'

    stripe_refund_id = db.Column(db.Unicode, primary_key=True, nullable=False)
    charge_id = db.Column(None, db.ForeignKey(
        'stripe_charges.charge_id', ondelete='cascade'), nullable=False)
    amount = db.Column(db.Integer, nullable=False, default=0)
    currency = db.Column(db.Unicode)
    currency_recorded_usd_exchange_rate = db.Column(db.Numeric(
        precision=10, scale=7))
    created = db.Column(db.Unicode)
    status = db.Column(db.Unicode, nullable=False)

    charge = db.relationship('StripeCharge', backref='refunds')
