import uuid
import bcrypt
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from flask import current_app, g

from . import db
from b2bapi.utils.randomstr import randomstr

class Signin(db.Model):
    __tablename__='signins'
    signin_id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    email = db.Column(db.Unicode, unique=True)
    passcode = db.Column('passcode', db.Unicode, nullable=True)
    passcode_timestamp = db.Column(db.DateTime)
    sent = db.Column(db.Boolean, default=False)

    #def authenticate(self, passcode):
    #    if not self.passcode==passcode:
    #        self.failure += 1
    #        return False
    #    self.failure = 0
    #    return True
    #    # TODO:  update `last_successful` to datetime.now()
    #        

    #def clear_passcode(self):
    #    self.passcode = None

    #def get_token(self, token_type='access_token', status='active'):
    #    for i,t in enumerate(self.meta.get('tokens', [])):
    #        if t.get('type')==token_type and t.get('status')==status:
    #            return t

    #@classmethod
    #def generate_token(cls, **kw):
    #    token_type = kw.pop('token_type')
    #    key = randomstr(32)
    #    token = f'{token_type}_{key}'
    #    status = kw.pop('status', 'pending')
    #    token = {
    #        'type': token_type,
    #        'status': status,
    #        'token': token,
    #        'timestamp': datetime.datetime.utcnow().isoformat(),
    #        **kw,
    #    }
    #    return token

    #def set_token(self, **kw):
    #    token = self.generate_token(**kw)
    #    self.meta.setdefault('tokens', []).append(token)
    #    return token

    #def remove_tokens(self, token_types=None):
    #    if token_types is None: # clear all tokens
    #        self.meta['tokens'][:] = []
    #        return
    #    try:
    #        self.meta['tokens'][:] = (t for t in self.meta['tokens']
    #                                  if t['type'] not in token_types)
    #    except (KeyError, IndexError) as e:
    #        pass



# TODO: ENABLE class UserView(db.Model): __abstract__=True
# TODO: ENABLE view_mapper('users_view', User.__table__.select(), db.metadata, UserView, 
# TODO: ENABLE             db.Column('user_id', db.Integer, db.ForeignKey(
# TODO: ENABLE                 'users.user_id'), primary_key=True))
