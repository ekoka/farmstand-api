import pytest
from vino.api.schema import obj, arr, prim
from vino.processors import validating as vld
from vino import errors as vno_err
from appsrc.api.validation.accounts import (
    password_check, new_account_via_google, new_account_via_email)
from appsrc.db.models.accounts import Account


@pytest.fixture
def datachecker():
    return obj(
        vld.allowempty,
        password_check.apply_to('password'),
    )


def test_string_less_than_8_characters_rejected(datachecker):
    data = {'password': '92kx9SK'}
    with pytest.raises(vno_err.ValidationErrorStack) as e_info:
        datachecker.validate(data)
    err_stack = e_info.value
    err_str = str(err_stack[0])
    assert 'too short' in err_str
    assert '8 characters or more' in err_str

def test_password_not_required(datachecker):
    data = {}
    datachecker.validate(data)

def test_null_value_removed(datachecker,):
    data = {'password': None}
    #with pytest.raises(vno_err.ValidationErrorStack) as e_info:
    #    datachecker.validate(data)
    #err_stack = e_info.value
    #err_str = str(err_stack[0])
    #assert 'must not be null' in err_str
    result = datachecker.validate(data)
    assert 'password' not in result

def test_empty_value_removed(datachecker):
    data = {'password': ''}
    #with pytest.raises(vno_err.ValidationErrorStack) as e_info:
    #    datachecker.validate(data)
    #err_stack = e_info.value
    #err_str = str(err_stack[0])
    #assert 'must not be empty' in err_str
    result = datachecker.validate(data)
    assert 'password' not in result



#@pytest.mark.skip('requires common_words database table')
def test_common_words_rejected(datachecker, load_common_words, db_session):
    load_common_words(db_session.connection())
    for pw in ['softball', 'password', 'valentin']:
        data = {'password': pw}
        with pytest.raises(vno_err.ValidationErrorStack) as e_info:
            datachecker.validate(data)
        err_stack = e_info.value
        err_str = str(err_stack[0])
        assert 'is too common' in err_str

def test_char_sequences_rejected(datachecker):
    for pw in ['23456789', 'hijklmno', 'vutsrqpo', '76543210']:
        data = {'password': pw}
        with pytest.raises(vno_err.ValidationErrorStack) as e_info:
            datachecker.validate(data)
        err_stack = e_info.value
        err_str = str(err_stack[0])
        assert 'is not safe' in err_str

def test_repeated_char_sequence_rejected(datachecker):
    for pw in ['222222222222222', '777777777777777', '999999999999999999999',
               'aaaaaaaaaaa']:
        data = {'password': pw}
        with pytest.raises(vno_err.ValidationErrorStack) as e_info:
            datachecker.validate(data)
        err_stack = e_info.value
        err_str = str(err_stack[0])
        assert 'is not safe' in err_str

def test_google_account_data_normalized():
    data = {
        'email': 'abc@def',
        'email_verified': True,
        'given_name': 'abc',
        'family_name': 'def',
        'password': '982kd2o29d8',
        'locale': 'fr',
    }
    result = new_account_via_google.validate(data)
    assert 'given_name' not in result and result['first_name']==data[
        'given_name']
    assert 'email_verified' not in result and result['confirmed']==data[
        'email_verified']
    assert 'locale' not in result and result['lang']==data[
        'locale']
    assert 'password' not in result


def test_email_account_data_normalized(app): # test needs context for password validation
    data = {
        'email': 'abc@def',
        'confirmed': True,
        'email_verified': True,
        'given_name': 'abc',
        'first_name': 'abc',
        'last_name': 'def',
        # context is needed for common_words check
        'password': '982kd2o29d8',
        'lang': 'fr',
    }
    result = new_account_via_email.validate(data)
    assert result['email']==data['email']
    assert result['confirmed']==False
    assert 'email_verified' not in result
    assert 'given_name' not in result
    assert result['password']==data['password']
    assert result['lang']==data['lang']
