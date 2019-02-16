import functools
from flask import redirect, g, request, current_app as app, abort
from sqlalchemy import exc as sql_exc
from sqlalchemy.orm import exc as orm_exc

#from .validation import signins as val
from b2bapi.db import db
from b2bapi.db.models.signins import Signin
from b2bapi.db.models.accounts import Account
from ._route import route, hal, json_abort
    
#@route('/clients', methods=['POST'], expects_data=True)
#def post_client(data):
#    data = val.new_client.validate(data)
#    try:
#        client = Client(**data)
#        db.session.add(client)
#        db.session.flush()
#    except sql_exc.IntegrityError as e:
#        db.session.rollback()
#        abort(400, 'Problem creating Client. Client may already exist.')
#    location = APIUrl('api_v1.get_client', client_name=client.name)
#    return {'location': location}, 201, [('Location', location)]

@route('/passcode', methods=['POST'], expects_data=True, domained=False)
def post_passcode(data):
    try:
        email = data.get('email')
        acc = Account.query.filter_by(email=email).one() 
    except orm_exc.NoResultFound:
        json_abort(404, {'error':'Email is not associated with an account.'})

    db.session.execute(
        db.text('delete from signins where email=:email'),
        params={'email':email},)
    signin = Signin(email=email, meta={'auth_type': 'login'})
    db.session.add(signin)
    return {}, 200, []


@route('/signins', methods=['POST'], expects_data=True, domained=False)
def post_signin(data):
    # TODO: validation
    # data = val.new_signin.validate(data)
    email = data.pop('email')
    # verify if an account has been created with that email in the past
    account = Account.query.filter_by(email=email).first() 
    if not account:
        json_abort(404, {'error': 'No account associated with this e-mail.'})

    # if account has been created create a Signin record.
    # A task queue will send an email to the address with an access code.
    # When access code is used, account will be confirmed if not yet done. 
    try:
        # first delete possible past signings with this email
        db.session.execute(
            db.text('delete from signins where email=:email'),
            params={'email':email})
        # then create new signin
        signin = Signin(email=email)
        db.session.add(signin)
        db.session.flush()
    except sql_exc.IntegrityError as e:
        db.session.rollback()
    except:
        db.session.rollback()
        raise
        json_abort(400, {'error': 'Problem creating Signin.'})

    return {}, 200, []

#@route('/signins/<signin_id>', methods=['DELETE'], expects_data=True,
#       domained=False)
#def delete_signin(signin_id, data):
#    try:
#        Signin.query.filter(
#            Signin.signin_id==signin_id).delete()
#        db.session.flush()
#        return {}, 200, []
#    except:
#        db.session.rollback()
#        raise
#        return {'error': 'Forbidden'}, 403, []
#
#
#@route('/signin/password', methods=['POST'], domained=False,
#       expects_data=True, expects_user=True, access_token_auth=True)
#def post_signin_password(user, data):
#    # user can only change their password
#    #TODO validation
#    # data = val.change_password.validate(data)
#    signin = user 
#    if not signin:
#        return {}, 200, []
#
#    try:
#        signin.password = data['password']
#        signin.remove_tokens(token_types=['access_token'])
#        signin.remove_tokens(token_types=['reset_token'])
#        token = signin.set_token(token_type='access_token', status='active')
#        db.session.flush()
#        return {'access_token': token}, 200, []
#    except:
#        raise
#        db.session.rollback()
#        return {}, 400, []
#
#@route('/signin/access-token', methods=['POST'], basic_auth=True, 
#       expects_user=True)
#def post_signin_access_token(user):
#    try:
#        token = user.set_token(token_type='access_token', status='active')
#        db.session.flush()
#    except:
#        db.session.rollback()
#        return {'error': 'Could not create token'}, 400, []
#    return {'access_token': token}, 200, []
#
#@route('/profile', methods=['GET'], basic_auth=True, expects_user=True)
#def get_profile(user):
#    return dict(
#        self=APIUrl('api_v1.get_profile'),
#        email=user.email,
#        token=user.get_token(token_type='access_token', status='active'),
#    ), 200, []
#
#@route('/activation', methods=['POST'], expects_data=True)
#def post_activation(data):
#    try:
#        token = data['activation_token']
#        token_expr = {'tokens': [
#            {
#                'type': 'activation_token', 
#                'token': token, 
#                'status': 'active',
#            },
#        ]}
#        signin = Signin.query.filter(
#            Signin.meta.comparator.contains(token_expr)).one()
#        signin.confirmed = True
#        signin.remove_tokens(token_types=['activation_token'])
#        db.session.flush()
#        return {}, 200, []
#    except:
#        db.session.rollback()
#        json_abort(400, {'error': 'Missing or invalid activation token.'})
#
#
#@route('/activation-token', methods=['POST'],
#       expects_data=True)
#def post_activation_token(data):
#    #TODO: validation of data
#    message = ('A message has been sent to any unconfirmed account with '
#        'that email address.')
#    try:
#        signin = Signin.query.filter(
#            # TODO move strip() to validation
#            Signin.email==data['email'].strip(), 
#            Signin.confirmed==False,
#            ).one()
#        signin.remove_tokens(token_types=['activation_token'])
#        signin.set_token(
#            token_type='activation_token', 
#            activation_url_template=data['activation_url_template'],
#            lang=data.get('lang', 'en'),
#            status='new',
#        )
#        db.session.flush()
#    except:
#        db.session.rollback()
#
#    return {'message': message}, 200, [] 
#
#
#@route('/signin', expects_params=True)
#def get_signin(params):
#    signin = find_signin_by_credentials(params)
#    if signin:
#        # TODO: put some info in rv
#        return {}, 200, []
#    return {'error': 'Missing profile or bad authentication.'}, 404, []
#
#def find_signin_by_credentials(creds, allowed_methods=None):
#    all_methods = ['password', 'access_token', 'temp_access_token']
#
#    if allowed_methods is None:
#        allowed_methods = all_methods
#
#    if 'password' in allowed_methods:
#        try:
#            # find signin based on email:password
#            signin = Signin.query.filter(
#                Signin.email==creds['username']).one()
#            if signin.authenticate(creds['password']):
#                return signin
#        except (KeyError, orm_exc.NoResultFound) as e:
#            pass
#
#    if 'access_token' in allowed_methods:
#        try:
#            # find signin based on token
#            token = creds['access_token']
#            token_expr = {'tokens': [{'token': token, 'status': 'active'}]}
#            signin = Signin.query.filter(
#                Signin.meta.comparator.contains(token_expr)).one()
#            return signin
#        except (KeyError, orm_exc.NoResultFound) as e:
#            pass
#
#@route('/signin/access-token', 
#       methods=['GET'], expects_params=True)
#def get_signin_access_token(params):
#    """
#    Similar to POST but returns existing token. Only generating a new one if
#    one has not been found.
#    """
#    token = None
#    signin = find_signin_by_credentials(params)
#    for t in signin.meta.setdefault('tokens', []):
#        if t['type']=='access_token' and t['status']=='active':
#            token = t
#    if not token:
#        token = signin.set_token(token_type='access_token', status='active')
#    db.session.flush()
#    return {'access_token': token}, 200, []
#
## a request to have a temporary token created
#@route('/signin/reset-token', 
#       methods=['POST'], expects_data=True)
#def post_signin_reset_token(data):
#    #TODO : validation
#    # data = val.password_reset_token.validate(data)
#    # get signin
#
#    unconditional_response = {}, 200, []
#
#    try:
#        signin = db.session.query(Signin).filter_by(
#            email=data['email']).one()
#    except orm_exc.NoResultFound as e:
#        return unconditional_response
#    signin.remove_tokens(token_types=['reset_token'])
#    signin.set_token(
#        token_type='reset_token',
#        reset_url_template=data['reset_url_template'],
#        lang=data['lang'],
#        status='new',
#    )
#    try:
#        db.session.flush()
#    except:
#        db.session.rollback()
#        # only if we have an actual db problem
#        abort(500)
#
#    return unconditional_response
