import simplejson as json
import stripe 

from .. import db
from ..models.billing import Plan
from ..models.security import CommonWord, ReservedWord

def run(app):
    with app.app_context():
        fncs = globals()
        try:
            for fncname, enabled in app.config['APP_INIT_CALLBACKS']['DB']:
                if enabled:
                    fnc = fncs[fncname]
                    fnc(app)
            db.session.commit()
        except:
            db.session.rollback()

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
    db.session.flush()

def sync_common_words(app):
    """
    populate common_words db table to check against obvious passwords.
    """
    db_words =  {w.word:w for w in CommonWord.query.all()}
    cw_file = app.config['COMMON_WORDS_FILE']
    wordset = set([]) 
    with open(cw_file) as f:
        wordset = set(json.loads(f.read()))

    # delete from db
    for w in set(db_words).difference(wordset):
        db.session.delete(db_words[w])
    
    # insert into db
    for w in wordset.difference(db_words):
        db.session.add(CommonWord(word=w))
    db.session.flush()

def sync_reserved_words(app):
    """
    populate reserved_words db table to avoid potentially problematic
    catalog registration.
    """
    db_words =  {w.word:w for w in ReservedWord.query.all()}
    rw_file = app.config['RESERVED_WORDS_FILE']
    wordset = set([]) 
    with open(rw_file) as f:
        wordset = set(json.loads(f.read()))

    # delete from db
    for w in set(db_words).difference(wordset):
        db.session.delete(db_words[w])
    
    # insert into db
    for w in wordset.difference(db_words):
        db.session.add(ReservedWord(word=w))
    db.session.flush()
