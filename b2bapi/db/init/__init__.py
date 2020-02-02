import stripe 

from .. import db
from ..models.billing import Plan

def create_db(app): 
    with app.app_context():
        db.create_all()

def sync_stripe_plans(app):
    if not app.config.get('UPDATE_FROM_STRIPE'):
        return
    with app.app_context():
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
