from datetime import datetime as dtm, timedelta
from flask import current_app as app
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc

from . import errors as err
from .utils import localize_data, delocalize_data, StripeContext
from .accounts import get_account
from ..db.models.domains import Domain, DomainAccount, DomainAccessRequest
from ..db.models.accounts import Account
from ..db.models.billing import Plan
from ..db import db
from ..db.models.reserved_words import reserved_words

def get_plan(plan_id):
    # service
    try:
        return Plan.query.filter_by(plan_id=plan_id).one()
    except orm_exc.NoResultFound as e:
        raise err.NotFound('Plan not found')

def delocalized_domain(domain, lang):
    domain.data = delocalize_data(domain.data, Domain.localized_fields, lang)
    rv._k('creation_date', domain.creation_date.date())
    return domain

def create_domain(data, access_token, lang):
    # service
    account = get_account(access_token['account_id'])
    try:
        name = data.pop('name')
    except KeyError:
        raise err.FormatError('Missing catalog identifier')
    if name in reserved_words:
        raise err.NotAuthorized('Unavailable domain name')
    plan = get_plan(plan_id=data.pop('plan_id', None))
    if not account.stripe_customer_id:
        raise err.NotAuthorized('Account does not have a linked Stripe account')
    trial_period_days = 30
    trial_end_date = dtm.utcnow() + timedelta(days=trial_period_days)
    month_after_trial = trial_end_date.replace(day=28) + timedelta(days=4)
    #next_month = dtm.now().replace(day=28) + timedelta(days=4)
    billing_cycle_anchor = int(month_after_trial.replace(day=1).timestamp())

    def duplicate_nicknames_handler(*a, **kw):
        raise err.Conflict(
            'The chosen catalog nickname is already taken, try a different one.')
    try:
        with StripeContext() as ctx:
            ctx.register_handler(
                error_type=sql_exc.IntegrityError,
                handler=duplicate_nicknames_handler,)
            # name the domain
            domain = Domain(name=name)
            # link to account
            domain.owner = account
            # set plan
            domain.plan = plan
            # activate
            domain.active = True
            db.session.add(domain)
            # add detailed information
            if data.get('data'):
                domain.data = localize_data(
                    data['data'], Domain.localized_fields, lang)
            domain.meta = data.get('meta') or Domain.default_meta()
            db.session.flush()
            # stripe's metadata
            metadata = {
                'domain_id': domain.domain_id,
                'domain_nickname': domain.name, }
            # If everything went well, start the meter.
            # Subscribe customer to plan on stripe.
            subscription = ctx.stripe.Subscription.create(
                customer=account.stripe_customer_id,
                items=[{'plan': plan.plan_id}],
                trial_period_days=trial_period_days,
                billing_cycle_anchor=billing_cycle_anchor,
                metadata=metadata,)
            # Link stripe data to local billable.
            domain.subscription_id = subscription.id
            domain.subscription_data = subscription
            # Also add a domain_accounts record for owner.
            da = set_domain_account(
                domain_id=domain.domain_id, account_id=account.account_id)
            da.role = 'admin'
            da.active = True
            db.session.flush()
    except err.Conflict: raise
    except: raise err.FormatError()
    return domain

def get_domains(access_token, lang):
    # service
    account = get_account(access_token['account_id'])
    roles = {account_domain.domain.name: account_domain.role
             for account_domain in account.domains}
    return (account, roles)


def get_domain_by_name(domain_name):
    # service
    try:
        return Domain.query.filter_by(name=domain_name).one()
    except orm_exc.NoResultFound as e:
        raise err.NotFound('Domain not found')

def get_domain(domain_name):
    # service
    try:
        return Domain.query.filter_by(name=domain_name).one()
    except orm_exc.NoResultFound as e:
        raise err.NotFound('Domain not found')

def update_domain(domain_name, data, lang):
    # service
    domain = get_domain_by_name(domain_name)
    # Changing localized data.
    domain.data = localize_data(
        data.get('data', {}), Domain.localized_fields, lang)
    # Changing metadata.
    domain.meta = data.get('meta', {})
    try:
        # Only change domain's active state if explicitly set in posted data.
        if data['active'] in (True, False):
            domain.active = data['active']
    except KeyError:
        pass
    try:
        db.session.flush()
    except:
        raise err.FormatError('Could not apply changes to domain')

def check_domain_name(name):
    # service
    if name in reserved_words:
        raise err.NotAuthorized('Unavailable domain name')
    try:
        return Domain.query.filter(Domain.name==name).one()
    except orm_exc.NoResultFound as e:
        raise err.NotFound('Domain not found')

def get_domain_account(domain_id, account_id):
    # service
    try:
        return DomainAccount.query.filter_by(
            domain_id=domain_id, account_id=account_id).one()
    except (orm_exc.NoResultFound, orm_exc.MultipleResultsFound):
        raise err.NotFound('Account not found')

def set_domain_account(domain_id, account_id):
    # service
    try:
        return get_domain_account(domain_id, account_id)
    except orm_exc.NoResultFound:
        # Only create a new domain if it was not found.
        rv = DomainAccount(domain_id=domain_id, account_id=account_id)
        db.session.add(rv)
        db.session.flush()
        return rv

def create_domain_account(data, domain):
    # service
    try:
        da = set_domain_account(domain_id=domain.domain_id, account_id=data['account_id'])
        da.active = True
        da.role = data.get('role', 'user')
        db.session.flush()
    except:
        db.session.rollback()
        raise err.FormatError('Could not add account to domain')

def delete_domain_account(account_id, domain):
    # service
    try:
        dom_acc = get_domain_account(domain_id=domain.domain_id, account_id=account_id)
        dom_acc.active = False
    except orm_exc.NoResultFound:
        db.session.rollback()

def get_domain_accounts(domain, active):
    # service
    q = DomainAccount.query.filter_by(domain_id=domain.domain_id)
    if active:
        q = q.filter_by(active=active)
    return q.all()

def create_access_request(account, data):
    # service
    try:
        domain = Domain.query.filter_by(name=data.get('domain')).one()
    except orm_exc.NoResultFound:
        raise err.NotFound('Domain not found.')
    access_request = DomainAccessRequest(
        account_id=account['account_id'],
        domain_id=domain.domain_id,
        creation_date=dtm.utcnow(),
        status="pending",
        data={
            'message': data.get('message'),
            'fields': data.get('fields'), },)
    db.session.add(access_request)
    try:
        db.session.flush()
    except sql_exc.IntegrityError:
        db.session.rollback()
        raise err.Conflict("A recent access request was already created.")
    return domain

def get_access_request_by_account(domain_id, account):
    # service
    try:
        return DomainAccessRequest.query.filter_by(
            domain_id=domain_id, account_id=account['account_id']).one()
    except orm_exc.NoResultFound:
        raise err.NotFound('Access request not found.')
    except orm_exc.MultipleResultsFound:
        raise err.Conflict('Multiple access requests found.')

def get_domain_access_requests(domain, lang):
    # service
    return DomainAccessRequest.query.filter_by(domain_id=domain.domain_id).all()

def get_access_request_by_id(access_request_id):
    # service
    try:
        return DomainAccessRequest.query.filter_by(
            access_request_id=access_request_id).one()
    except orm_exc.NoResultFound:
        raise err.NotFound('Access request not found')

def update_access_request_status(access_request_id, status):
    # service
    access_request = get_access_request_by_id(access_request_id)
    access_request.status = status
    db.session.flush()
