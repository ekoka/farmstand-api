import uuid
import bcrypt
import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from flask import current_app, g

from . import db
from b2bapi.utils.randomstr import randomstr

class Signin(db.Model):
    __tablename__='signins'
    signin_id = db.Column(db.UUID, primary_key=True, default=uuid.uuid4)
    email = db.Column(db.Unicode, unique=True)
    _password = db.Column('password', db.Unicode)
    confirmed = db.Column(db.Boolean, default=False)
    failure = db.Column(db.Integer)
    last_successful = db.Column(db.DateTime)
    meta = db.Column(db.JSONB, default=dict)
    data = db.Column(db.JSONB, default=dict)
    """
        {
            "tokens": [
                {
                    'type': 'access_token', # temporary, confirmation
                    'status': 'active', # pending, delete
                    'token': ...
                },
            ], 
        }
    """

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = encrypt_password(password)


    @classmethod
    def login(cls, password):
        s = cls.query.filter(cls.email==email).one()
        if s.authenticate(password):
            # create an access token for user_id
            jwt = create_jwt_token(u)
            # TODO: register token in redis
            return jwt

    def authenticate(self, password):
        # password must be an unicode object
        try:
            password = password.encode('utf-8')
            return self.password==bcrypt.hashpw(
                password, self.password.encode('utf-8')).decode('utf-8')
        except AttributeError:
            return False

    def get_token(self, token_type='access_token', status='active'):
        for i,t in enumerate(self.meta.get('tokens', [])):
            if t.get('type')==token_type and t.get('status')==status:
                return t

    @classmethod
    def generate_token(cls, **kw):
        token_type = kw.pop('token_type')
        key = randomstr(32)
        token = f'{token_type}_{key}'
        status = kw.pop('status', 'pending')
        token = {
            'type': token_type,
            'status': status,
            'token': token,
            'timestamp': datetime.datetime.utcnow().isoformat(),
            **kw,
        }
        return token

    def set_token(self, **kw):
        token = self.generate_token(**kw)
        self.meta.setdefault('tokens', []).append(token)
        return token

    def remove_tokens(self, token_types=None):
        if token_types is None: # clear all tokens
            self.meta['tokens'][:] = []
            return
        try:
            self.meta['tokens'][:] = (t for t in self.meta['tokens']
                                      if t['type'] not in token_types)
        except (KeyError, IndexError) as e:
            pass


def encrypt_password(password):
    password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    pwhash = bcrypt.hashpw(password, salt)
    # return in unicode
    return pwhash.decode('utf-8')


# TODO: ENABLE class UserView(db.Model): __abstract__=True
# TODO: ENABLE view_mapper('users_view', User.__table__.select(), db.metadata, UserView, 
# TODO: ENABLE             db.Column('user_id', db.Integer, db.ForeignKey(
# TODO: ENABLE                 'users.user_id'), primary_key=True))
