import functools
from flask import redirect, g, request, current_app as app, abort
from sqlalchemy import exc as sql_exc
from sqlalchemy.orm import exc as orm_exc

#from .validation import signins as val
from b2bapi.db import db
from b2bapi.db.models.accounts import Account, Signin
from ._route import route, hal, json_abort
from b2bapi.utils.randomstr import randomstr

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
    # When access code is used, account will be confirmed if it isn't yet. 
    try:
        # first delete possible past signings with this email
        db.session.execute(
            db.text('delete from signins where email=:email'),
            params={'email':email})
        # then create new signin
        signin = Signin(
            email=email, 
            passcode=randomstr(4, ucase=False, lcase=True, digits=True),
        )
        db.session.add(signin)
        db.session.flush()
    except sql_exc.IntegrityError as e:
        db.session.rollback()
    except:
        db.session.rollback()
        raise
        json_abort(400, {'error': 'Problem creating Signin.'})

    return {}, 200, []
