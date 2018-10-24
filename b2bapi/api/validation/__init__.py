import uuid
from vino.api import schema as vno_shm
from vino import utils as vno_uls
from vino import errors as vno_err
from vino.processors import validating as vld
from flask import g


#TODO: vno_uls.empty_values

def set_value(value):
    return lambda*a,**k: value

def set_tenant(*a, **k):
    return g.tenant['tenant_id']

class set_default:
    def __init__(self, fnc, replaceables=(None,)):
        self.fnc = fnc
        self.replaceables = replaceables

    def run(data=vno_uls._undef, state=None):
        if data is vno_uls._undef or data in self.replaceables:
            return self.fnc(data, state)
        return data

def check_uuid4(data, state=None):
    try:
        return uuid.UUID(str(data), version=4).hex
    except ValueError:
        raise vno_err.ValidationError('Invalid UUID')

def set_uuid(data, state):
    return uuid.uuid4().hex

                                                                                
def upper(data, state=None):
    try:
        return data.upper()
    except AttributeError:
        return data

def remove(data, state=None):
    return vno_uls._undef

def check_bool(data, state=None):
    if vno_uls.is_boolean(data, int_as_bool=True):
        return bool(data)
    raise vno_err.ValidationError('Expected valid boolean: true|false or 1|0.')
