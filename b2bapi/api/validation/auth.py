import bcrypt
from flask import current_app as app
from vino.api.schema import obj, arr, prim
from vino.processors import validating as vld

from simpleauth.db.models.signins import Client, Signin

from . import check_uuid4,  set_uuid, upper, remove, set_value
from simpleauth.utils.randomstr import randomstr

def set_authkey(*a, **k):
    prefix = 'authkey_'
    return  prefix + randomstr(20)

def check_password(data, state=None):
    return data

def encrypt_password(data, state):
    password = data.encode('utf-8')
    salt = bcrypt.gensalt()
    pwhash = bcrypt.hashpw(password, salt)
    # return in unicode
    return pwhash.decode('utf-8')

def authenticate(self, password):
    # password must be an unicode object
    password = password.encode('utf-8')
    return self.password==bcrypt.hashpw(
        password, self.password.encode('utf-8')).decode('utf-8')

def check_email(data, state=None):
    return data

def check_client(data, state=None):
    c = Client.query.filter_by(name=data['client_name']).one()
    return data

def init_meta(data, state):
    token = Signin.generate_token(token_type='access_token', status='active')
    rv = {'tokens': [token]}
    return rv

def remove_client_data(data, state=None):
    data.pop('client_name', None)
    data.pop('client_authkey', None)
    return data

client_urls = obj(
    prim(vld.required).apply_to('base_url'),
    prim(vld.required).apply_to('password_reset'),
)

# TODO: add an extrafield blocker
new_client = obj(
    prim(vld.required, vld.rejectempty, vld.rejectnull).apply_to('name'),
    prim(vld.required(default=set_authkey, override=set_authkey))
        .apply_to('authkey'),
    obj(vld.required(default=set_value({})),
        vld.allowempty).apply_to('meta'),
)

new_signin = obj(
    prim(vld.required(default=set_uuid), check_uuid4,).apply_to('signin_id'),
    prim(vld.required, vld.rejectempty, vld.rejectnull, check_email)
        .apply_to('email'),
    prim(vld.optional, vld.rejectempty, vld.rejectnull, check_password,
         encrypt_password,)
        .apply_to('password'),
    prim(vld.required).apply_to('client_name'),
    check_client,
    prim(vld.required(default=set_value(False), override=set_value(False)))
        .apply_to('confirmed'),
    obj(vld.required(default=init_meta, override=init_meta)).apply_to('meta'),
)

