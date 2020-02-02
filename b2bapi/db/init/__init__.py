import stripe 

from .. import db
from ..models.billing import Plan

def run(app):
    with app.app_context():
        fncs = globals()
        for fncname, enabled in app.config['APP_INIT_CALLBACKS']['DB']:
            if enabled:
                fnc = fncs[fncname]
                fnc(app)

def create_db(app): 
    db.create_all()

def sync_stripe_plans(app):
    db_plans = {p.data['id']:p for p in Plan.query.all()}
    stripe_plans = {p['id']:p for p in stripe.Plan.list(active=True).data}
    
    # to delete from db
    for plan_id, p in db_plans.items():
        if plan_id not in stripe_plans:
            db.session.delete(p)
    # to insert into db
    for plan_id, p in stripe_plans.items():
        if plan_id not in db_plans:
            db.session.add(Plan(
                plan_id=plan_id,
                plan_type='domain',
                data=p,
            ))
    db.session.commit()


def sync_reserved_words(app):
    ...
