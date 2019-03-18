import bcrypt
from flask import current_app as app
from vino.api.schema import obj, arr, prim
from vino.processors import validating as vld
from vino import errors as vno_err
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc

from b2bapi.db.models.accounts import Signin
from b2bapi.db.models.security import Word

from . import check_uuid4,  set_uuid, upper, remove, set_value
from b2bapi.utils.randomstr import randomstr

def max_size(size):
    def validate(data, state):
        if len(data) <= size:
            return data
        raise vno_err.ValidationError(f'Password is too long. '
                                      f'Must be {size} characters or less.')
    return validate

def min_size(size):
    def validate(data, state):
        if len(data) >= size:
            return data
        raise vno_err.ValidationError(f'Password is too short. '
                                      f'Must be {size} characters or more.')
    return validate

def padless_size(minsize):
    def validate(data, state):
        if len(data.strip()) >= minsize:
            return data
        raise vno_err.ValidationError('Password is not safe.')
    return validate

def dictionary_match(dictionary='john'):
    if dictionary in ['*', None]:
        dictionary = None
    def validate(data, state):
        try: 
            q = Word.query.filter_by(word=data)
            if dictionary:
                q = q.filter(Word.dictionary==dictionary)
            q.one()
        except orm_exc.NoResultFound as e: 
            # we didn't find it in the dict, it may be secure
            return data
        raise vno_err.ValidationError('Password is too common.')
    return validate



def alphanum_sequence(minlength=None):
    def validate(data, state):
        # if the data is 2 characters or less, a sequence is the least of our
        # problems. Let another validator take care of this.
        if len(data) <= 2:
            return data
        # beyond the minimum length, sequences are considered safe enough
        # for other contingencies to take over in case of a breach attempt.
        if minlength:
            if len(data) >= minlength:
                return data
        # we first assume that this is a sequence 
        # and we want to be proven wrong
        seq_asc = seq_desc = True
        # we'll be working with a generator of letter ordinals (integer)
        ordgen = (ord(char) for char in data)
        # let's get the first two values to compare
        left, right = next(ordgen), next(ordgen)
        # let's loop
        while True:
            try:
                # if the ascending flag is still up it means we're going up.
                # Idem if left is less than right by 1. 
                if seq_asc and left==right-1:
                    # we're ascending we can't be descending.
                    seq_desc = False
                # if the descending flag is still up it means we're going down.
                # Idem if left is greater than right by 1.
                elif seq_desc and left==right+1:
                    # we're descending we can't be ascending.
                    seq_asc = False
                else:
                    # we couldn't enter either of the previous selections.
                    # It's safe to say that we're not completely ascending nor
                    # descending.
                    seq_desc = seq_asc = False
                    # We're also done.
                    break
                # when we move left becomes right and right gets the next value
                left, right = right, next(ordgen)
            except StopIteration: 
                # end of string
                break

        if seq_desc or seq_asc:
            raise vno_err.ValidationError('Password is not safe.')
        return data
    return validate


def repeated_char(minlength=None):
    def validate(data, state):
        # if the data is 2 characters or less, a sequence is the least of our
        # problems. Let another validator take care of this.
        if len(data) <= 2:
            return data
        # beyond the minimum length, sequences are considered safe enough
        # for other contingencies to take over in case of a breach attempt.
        if minlength:
            if len(data.strip()) >= minlength:
                return data

        if len(set(data))==1:
            raise vno_err.ValidationError('Password is not safe.')
        return data
    return validate
    

password_check = prim(
    ~vld.required,
    vld.rejectempty,
    vld.rejectnull,
    max_size(200),
    min_size(8),
    padless_size(6),
    dictionary_match(dictionary='john'), # john the ripper
    alphanum_sequence(minlength=30),
    repeated_char(minlength=50),
)


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


#new_signin = obj(
#    prim(vld.required(default=set_uuid), check_uuid4,).apply_to('signin_id'),
#    prim(vld.required, vld.rejectempty, vld.rejectnull, check_email)
#        .apply_to('email'),
#    prim(vld.optional, vld.rejectempty, vld.rejectnull, check_password,
#         encrypt_password,)
#        .apply_to('password'),
#    prim(vld.required).apply_to('client_name'),
#    check_client,
#    prim(vld.required(default=set_value(False), override=set_value(False)))
#        .apply_to('confirmed'),
#    obj(vld.required(default=init_meta, override=init_meta)).apply_to('meta'),
#)

