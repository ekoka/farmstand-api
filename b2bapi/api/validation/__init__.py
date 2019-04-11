import uuid
from vino.api import schema as vno_shm
from vino import utils as vno_uls
from vino import errors as vno_err
from vino.processors import validating as vld, processors as prc
from flask import g


#TODO: vno_uls.empty_values

def set_value(value):
    return lambda*a,**k: value

def has_any(*values):
    def rv(data, state=None):
        if data in values:
            return data
        raise vno_err.ValidationError(f'"{data}" is not in {values}')
    return rv

valid_values = has_any


def set_domain(*a, **k):
    return g.domain.domain_id

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

def set_uuid(data, state=None):
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

class ExtraProperties(prc.Processor):
    __possible_actions__ = ('raise', 'remove', 'ignore')
    def __init__(self, action='remove'):
        if action not in ExtraProperties.__possible_actions__:
            #TODO better message
            raise vno_err.VinoError('Action not recognized')
        self.action = action

    def run(self, data, state):
        try:
            self.matches = state['matches']
        except (TypeError, KeyError) as e:
            #TODO better message
            raise vno_err.VinoError('processor used in wrong context')

        if self.action=='remove':
            return self._remove_if_not_matched(data)
        elif self.action=='raise':
            return self._raise_if_not_matched(data)
        # else we 'ignore'
        return data

    def _raise_if_not_matched(self, data):
        for k in data.keys():
            if k not in self.matches['by_key']:
                raise vno_err.ValidationError('Key not in schema')
        # if all went well we simply return data to stay consistent with 
        # common usage.
        return data

    def _remove_if_not_matched(self, data):
        rv = {}
        for k,value in data.items():
            if k in self.matches['by_key']:
                rv[k] = value
        return rv
