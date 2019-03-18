import bcrypt
from vino.api.schema import prim
from vino.processors import validating as vld
from vino import errors as vno_err
from sqlalchemy.orm import exc as orm_exc

from b2bapi.db.models.security import Word


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

def encrypt_password(password):
    password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    # returns a binary string within the ascii range
    pwhash = bcrypt.hashpw(password, salt)
    # return as unicode
    return pwhash.decode('utf-8')

def match_passwords(encrypted_password, plain_password):
    #TODO: figure out what to do if user sends us a string outside of unicode
    # plan password arrives in unicode
    plain_password = plain_password.encode('utf-8')
    return encrypted_password==bcrypt.hashpw(
        plain_password, encrypted_password.encode('utf-8')).decode('utf-8')
