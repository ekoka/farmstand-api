from sqlalchemy import exc as sql_exc

#from .validation import signins as val
from ..utils.randomstr import randomstr
from ..db import db
from ..db.models.accounts import Account, Signin
from . import errors as err

def create_signin(data):
    # TODO: validation
    # data = val.new_signin.validate(data)
    email = data.pop('email')
    # verify if an account has been created with that email in the past
    account = Account.query.filter_by(email=email).first()
    if not account:
        raise err.NotFound('No account associated with this e-mail.')
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
            passcode=randomstr(4, ucase=False, lcase=True, digits=True),)
        db.session.add(signin)
        db.session.flush()
    except sql_exc.IntegrityError as e:
        db.session.rollback()
        raise err.FormatError('Could not create sign-in record.')
    return signin
