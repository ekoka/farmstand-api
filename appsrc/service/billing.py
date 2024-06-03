from sqlalchemy.orm import exc as orm_exc

from ..db.models.billing import Plan
from ..db.models.accounts import PaymentSource
from ..db import db
from .utils import StripeContext

from . import accounts as acc_srv

def get_plan(plan_id):
    # service
    try:
        return Plan.query.filter_by(plan_id=plan_id).one()
    except orm_exc.NoResultFound:
        raise err.NotFound('Plan not found')

def get_plans():
    # service
    plans = Plan.query.all()
    def amount(p):
        try:
            return p.data['amount']
        except:
            return 0
    return sorted(plans, key=amount)

def add_payment_source(account_id, token):
    # service
    #TODO: validation
    # data = payment_source.validate(data)
    account = acc_srv.get_account(account_id)
    with StripeContext() as ctx:
        customer = ctx.stripe.Customer.retrieve(account.stripe_customer_id)
        source = customer.sources.create(source=token['id'])
        customer.refresh()
        account.payment_sources.append(PaymentSource(
            source_id=source.id,
            data=source,
            default_source=customer.default_source==source.id,))
        db.session.flush()
    return account.payment_sources[-1]

def get_payment_sources(account_id):
    # services
    try:
        return PaymentSource.query.filter_by(account_id=account_id).all()
    except:
        raise err.ServiceError('Could not retrieve payment sources')

def delete_payment_source(source_id, account_id):
    # service
    account = acc_srv.get_account(account_id)
    sources = PaymentSource.query.filter_by(account_id=account_id).all()
    with StripeContext() as ctx:
        customer = ctx.stripe.Customer.retrieve(account.stripe_customer_id)
        customer.sources.retrieve(source_id).delete()
        customer.refresh()
        # Update the current sources.
        for s in sources:
            if s.source_id==source_id:
                # Pop delete source.
                db.session.delete(s)
            else:
                # Update default flag on remaining sources.
                s.default_source = s.source_id==customer.default_source
