from . import db
from uuid import uuid4
from datetime import datetime as dtm, timedelta

class Plan(db.Model):
    __tablename__ = 'plans'

    plan_id = db.Column(db.Integer, primary_key=True)
    stripe_plan_id = db.Column(db.Unicode, unique=True)
    name = db.Column(db.Unicode, unique=True)
    # allows to filter a type of plan. Mostly useful for listing different pricing 
    # for the same type of plans e.g. "catalog".
    plan_type = db.Column(db.Unicode)
    price = db.Column(db.Integer)
    cycle = db.Column(db.Unicode) # null, daily, weekly, monthly
    # details on the particulars of the offering
    data = db.Column(db.JSONB, default=dict)

    localized_fields = ['label', 'options']

class BillingError(Exception):
    pass

class Billable(db.Model):
    __tablename__ = 'billables'
    billable_id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(None, db.ForeignKey('plans.plan_id'))
    owner_account_id = db.Column(None, db.ForeignKey(
        'accounts.account_id', ondelete='restrict'), nullable=False)
    # discriminator property (e.g. `domains`)
    relation = db.Column(db.Unicode)
    active = db.Column(db.Boolean)
    # recorded price and recurrence, in case underlying plan changes
    price_timestamp = db.Column(db.DateTime)
    recorded_price = db.Column(db.Integer)
    recorded_cycle = db.Column(db.Unicode)
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

    def current_period_join():
        now = dtm.utcnow()
        last_month = lambda: now - timedelta(now.day)
        # current month
        return ((Billable.billable_id==BillablePeriod.billable_id) &
                (BillablePeriod.start_timestamp>last_month()) &
                (BillablePeriod.end_timestamp==None) & 
                (BillablePeriod.current))

    current_period = db.relationship(
        'BillablePeriod', primaryjoin=current_period_join, uselist=False)

    def init_period(self):
        if self.periods: 
            raise BillingError(
                'Billing Period already initialized on Billable.')
        self.start_period()
         
    def start_period(self, timestamp=None):
        if self.current_period:
            # only start a new period if there's not a current one
            raise BillingError(
                'All Billing Periods must be closed on Billable before '
                'opening a new one.')
        if timestamp is None:
            timestamp = dtm.utcnow()
        self.periods.append(BillablePeriod(
            billable_id=self.billable_id,
            start_timestamp = timestamp,
            # set default values for currently active period 
            end_timestamp = None,
            current = True,
            # if amount is None, it must be calculated 
            amount = None,
        ))
            

    def close_current_period(self):
        self.current_period.close()

db.Billable = Billable
    

class BillablePeriod(db.Model):
    __tablename__ = 'billable_periods'

    """
    - Periods are bound by the first and last day of the month.
    - A product/service has a single current period for the month.
        i.e. there's an unique combination of
            - current==true
            - product_id
            - month
            - year
    - Dates for a product should not overlap within a month.
    - The current period's `end_day` is unspecified (null) until `current` is
    set to false. Today's date is then timestamped.
    - The current period is automatically closed on the last day of the month.
    If the product is active, another period is automatically opened with the
    next day as a start date.
    - There should be only one current period per active product/service.
    - When an AccountBillable is deactivated the period is deactivated.
    - If a product is reactivated the same day it is deactivated the same period
    is reactivated.
    """
    billable_period_id = db.Column(db.Integer, primary_key=True)
    billable_id = db.Column(None, db.ForeignKey('billables.billable_id'))
    start_timestamp = db.Column(db.DateTime, default=dtm.utcnow())
    end_timestamp = db.Column(db.DateTime, nullable=True)
    current = db.Column(db.Boolean)
    # usage amount is recorded once the period closes, i.e. current==false
    # otherwise it is calculated in-app.
    _amount = db.Column('amount', db.Integer, nullable=True)

    billable = db.relationship(Billable, backref='periods')

    @property
    def amount(self):
        if self._amount is None:
            if self.billable.cycle is 'monthly': 
                price = self.billable.recorded_price or 0
                daily_price = price / self.days_in_month
                return daily_price * self.elapsed_time.days 
            # TODO: should raise an error as a billable without cycle
            # should just set the price in the amount.
            return None
        return self._amount

    @amount.setter
    def amount(self, value):
        self._amount = value

    @property
    def days_in_month(self):
        # move some day into the next month
        next_month = self.start_timestamp.replace(day=28) + timedelta(days=4)
        # remove x number of days, with x whatever the day in the next month is
        last_day_of_month = next_month - timedelta(next_month.day)
        return last_day_of_month.day
        # current month

    @property
    def end_or_current(self):
        if not getattr(self, '_end_or_current', None):
            self._end_or_current = self.end_timestamp or dtm.utcnow()
        return self._end_or_current

    def close(self):
        self.current = False
        self.end_timestamp = dtm.utcnow()
        self._end_or_current = None


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
