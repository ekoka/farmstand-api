import pytest
import requests
from datetime import datetime as dtm, timedelta


from b2bapi.db.models.billing import Plan, Billable, BillablePeriod
from b2bapi.api.billing import (
    billable_monthly_periods,
    period_day_count,
    period_charges,
    billable_report,
)
from ..conftest import cannot_reach_stripe

@pytest.mark.skip('use to dump periods')
def test_dump_periods(dump_periods, db_session):
    session = db_session
    dump_periods(session)

@pytest.mark.skipif(cannot_reach_stripe(), reason='Could not reach stripe')
def test_can_get_plans(load_pricing, nested_session, api_client, jsloads):
    load_pricing(nested_session.connection())
    data = jsloads(api_client.get('/api/v1/plans').data)
    assert len(data['plans']) > 0
    for p in data['plans']:
        assert p['object']=='plan'

def test_plans_are_delocalized(
    load_pricing, nested_session, api_client, jsloads):
    load_pricing(nested_session.connection())
    data = jsloads(api_client.get('/api/v1/plans?lang=fr').data)
    plan = nested_session.query(Plan).first()
    plan_data = [d for d in data['_embedded']['plans']
                 if plan.plan_id==d['plan_id']][0]
    assert plan_data['data']['label']==plan.data['label']['fr']


def test_can_fetch_all_monthly_periods_for_billable(load_periods, nested_session):
    session = nested_session
    load_periods(session.connection())
    b = nested_session.query(Billable).first()
    periods = billable_monthly_periods(b, 2018, 12)
    for p in periods:
        assert p.start_timestamp.month==12
        assert p.start_timestamp.year==2018
        assert p.end_timestamp.month==12
        assert p.end_timestamp.year==2018

def test_can_determine_period_day_count():
    period = BillablePeriod(
        start_timestamp=dtm(2018, 11, 2),
    )
    day_count = 20
    period.end_timestamp = period.start_timestamp + timedelta(days=20)
    assert period_day_count(period)==day_count

def test_can_determine_period_charges():
    period = BillablePeriod(
        start_timestamp=dtm(2018, 11, 2),
        end_timestamp=dtm(2018, 11, 7), # 5 days
    )
    period.billable = Billable(recorded_price=3500)
    assert period_charges(period)==round(3500*5/30)


@pytest.fixture
def billable_periods():
    intervals =  (3, 5, 7, 10)
    time_intervals =  (timedelta(days=i) for i in intervals)
    start_date = [dtm(2017, 10, 1)]
    def _period(ti):
        sd = start_date.pop()
        p = BillablePeriod(
            start_timestamp=sd,
            end_timestamp=sd + ti,
        )
        start_date.append(p.end_timestamp + timedelta(days=1))
        return p
    return [_period(ti) for ti in time_intervals]

def test_billable_monthly_report_can_break_down_usage_per_period(load_periods,
    billable_periods, logger, nested_session):
    load_periods(nested_session.connection())
    b = nested_session.query(Billable).first()
    b.recorded_price = 8900
    [b.periods.append(p) for p in billable_periods]
    nested_session.commit()
    r = billable_report(b, 2017, 10)
    assert len(r['reports'])==4
    assert r['total']==round(8900*(3+5+7+10)/31)


def test_opening_period_closes_previous_one():
    pass

def test_closing_period_sets_amount():
    pass

def test_invalid_dates_rejected_on_period():
    # future dates
    # overlapping dates
    # different months
    pass

