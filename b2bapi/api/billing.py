from flask import g, abort, current_app as app, jsonify, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err
import slugify
from datetime import datetime as dtm, timedelta
from functools import reduce

from b2bapi.db.models.domains import Domain
from b2bapi.db.models.billing import Plan, Billable, BillablePeriod
from b2bapi.db import db
from b2bapi.utils.uuid import clean_uuid
from ._route import route, url_for, json_abort, hal
from b2bapi.db.models.reserved_names import reserved_names
from .product_utils import _delocalize_data

def _plan_resource(p, lang='en'):
    rv = hal()
    rv._l('self', url_for('api.get_plan', plan_id=p.plan_id))
    rv._k('plan_id', p.plan_id)
    rv._k('name', p.name)
    rv._k('price', p.price)
    rv._k('cycle', p.cycle)
    rv._k('plan_type', p.plan_type)
    rv._k('details', _delocalize_data(p.details, ['label', 'options'], lang))
    return rv.document


@route('/plans/<plan_id>', domained=False, expects_lang=True)
def get_plan(plan_id, lang):
    try:
        plan = Plan.query.filter_by(plan_id=plan_id).one()
    except (orm_exc.NoResultFound):
        json_abort(404, {'error': 'Plan not found.'})
    return _plan_resource(plan, lang), 200, []

@route('/plans', expects_params=True, domained=False, expects_lang=True)
def get_plans(params, lang):
    plans = Plan.query.order_by(Plan.price.asc()).all()
    rv = hal()
    rv._l('self', url_for('api.get_plans'))
    rv._embed('plans', [_plan_resource(p, lang) for p in plans])
    return rv.document, 200, []

def billable_report(b, year, month):
    b_periods = billable_monthly_periods(b, year, month)
    period_reports =  [period_report(p) for p in b_periods]
    billable_total = lambda subtotal,r: subtotal + r['charges']
    total = reduce(billable_total, period_reports, 0)
    return dict(reports=period_reports, total=total)
       

@route('/usage/<year>/<month>', domained=False, expects_account=True)
def get_usage(account, year, month):
    # validate month and year
    # calculate month's daily charges

    # get all periods usage and associated charges
    billable_reports = {b.billable_id: billable_report(b, year, month) 
                        for b in account.billables}

    monthly_total = lambda total, b_report: total + b_report['total']
    monthly_report = dict(
        billabes=billable_report,
        monthly_total = reduce(monthly_total, billable_reports, 0),
    )

    rv = hal()
    rv._link('self', url_for('api.get_usage'))
    rv._k('current_usage', current_usage(account.billables))

def period_report(period):
    return {
        'billable_id': period.billable.billable_id,
        'start_date': period.start_timestamp, 
        'end_date': period.end_or_current, 
        'charges': period_charges(period),     
    }

def billable_monthly_periods(billable, year, month):
    first_day_of_month = dtm(year, month, 1)
    next_month = first_day_of_month + timedelta(days=31)
    first_day_of_next_month = next_month.replace(day=1)
    q = BillablePeriod.query.filter(
        BillablePeriod.start_timestamp>=first_day_of_month,
        BillablePeriod.start_timestamp<first_day_of_next_month,
        BillablePeriod.billable_id==billable.billable_id,
    ).order_by(BillablePeriod.start_timestamp.desc())
    return q.all()

def current_usage(billables):
    for b in billables:
        pass

def period_charges(period):
    # calculate day count in period
    # multiply by daily_charges
    rv = period_day_count(period) * daily_charges(
        period.billable.recorded_price, period.days_in_month)
    return round(rv)

def period_day_count(period):
    td = period.end_or_current - period.start_timestamp
    return td.days

def daily_charges(monthly_charge, days_in_month):
    #return period.billable.recorded_price / month_day_count(year, month)
    return monthly_charge / days_in_month

def month_day_count(year, month):
    # TODO
    return 30
