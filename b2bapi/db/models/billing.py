from . import db
from uuid import uuid4


class BillingItem(db.Model):
    __tablename__ = 'billing_items'

    billing_item_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode)
    recurrent_pricing = db.Column(db.Boolean)
    pricing_interval = db.Column(db.Unicode) # null, monthly, daily
    price = db.Column(db.Integer)
    details = db.Column(db.JSONB, default=dict)

class UsagePeriod(db.Model):
    __tablename__ = 'usage_periods'

    """
    - Usage periods are bound by the first and last day of the month.
    - A product/service has a single current period for the month.
        i.e. there's an unique combination of:
            - current==true
            - product_id
            - month
            - year
    - Dates for a product should not overlap within a month.
    - The current period's `end_day` is unspecified (null) until `current` is
    set to false. The current day's is then timestamped.
    - The current period is automatically closed on the last day of the month.
    If the product is active, another period is automatically opened with the
    next day as a start date.
    - There's should be only one current period per active product/service.
    - When a product is deactivated the period is deactivated.
    - If a product is reactivated the same day it is deactivated the same period
    is reactivated.
    """
    usage_period_id = db.Column(db.Integer, primary_key=True)
    billing_item_id = db.Column(None)
    month = db.Column(db.Integer)
    year = db.Column(db.Integer)
    start_day = db.Column(db.Integer)
    end_day = db.Column(db.Integer, nullable=True)
    current = db.Column(db.Boolean) 
