import pytest

from b2bapi.db.models.billing import Plan

@pytest.mark.skip('use to replace the pricing plan dump file')
def test_dump_pricing_plan_fixture(dump_pricing, nested_session):
    dump_pricing(nested_session)

def test_can_load_pricing_plans_from_dump(load_pricing, nested_session):
    load_pricing(nested_session.connection())
    plans = nested_session.query(Plan).all()
    assert len(plans)>0




