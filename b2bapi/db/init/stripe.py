from .. import db
from ..models.billing import Plan
import stripe 

def sync_stripe_plans(app):
    with app.app_context():
        db_plans = {p.data['id']:p for p in Plan.query().all()}
        stripe_plans = {sp['id']:sp for sp in stripe.Plan.list(active=True).data}
        
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
