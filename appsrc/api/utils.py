"""
How to handle data in arrays during a merge (i.e. during atomic updates)?

The following is a convention used within the API to manage data contained
in arrays in a way that facilitates atomic updates. It's not meant to become
a standard beyond the scope of this platform.

- During atomic updates we divide the use of arrays into two distinct groups:
    - the first group (group1) can only hold items of object data type.
    - the second (group2) can include the remaining types, namely bool, number,
    string and arrays.

- Objects cannot be placed in group2 arrays and boolean, string, number, and
arrays cannot go in group1.

- this implies that if an array directly contains an object, it's
automatically considered a group1 and its other items must also be objects.
An array can thus only hold items of a single group at a time.

- if a structure is needed to keep data of varying types, use an object to that
effect.

- all items in group1 must have an identifying field (i.e. a key) that is by
default expected to be called 'name' and which should hold a value that is
unique within the array. The key should remain consistent across the api (i.e.
don't call it "name" in one instance, "id" in another, and "key" in a third).


    [{'name': 'firstname', ...}, {'name': 'lastname', ...}, ...]

- the point of this key is to match the object to its stored counterpart
during an atomic update, thus making it possible to only upload the relevant
information without padding the array with placeholders.

- Note that during an atomic update of group1 objects, their order in the
array has no meaning. They are matched and updated based on their key.

- Although changes to dicts in group1 are made atomically group2 arrays are
update as a whole.

- It should be noted that if a group1 array happens to have a group2 ancestor
it cannot be updated atomically:

    e.g.
    group2[                             can hold (array, bool, number, string)
        group2[                         can hold (array, bool, numer, string)
            group1[{...}, ...],         can hold (object)
            group1[{...}, ...],
            group1[{...}, ...],
        ],
        bool,
        group2
        ...
    ]

This is because, since the ancestor group2 is assigned as a chunk, it thus
becomes impossible to accurately determine the descendant groups' targets.

A side effect of this limitation is that in this situation it is possible to
have mixed types in descendant group as the parser never gets a chance to
validate them.

My advice is to keep things as flat and simple as reasonably possible.
"""
from copy import deepcopy
import stripe

from ..db.models.meta import Field
from ..db import db
from .routes.routing import json_abort
from ..service import errors as srv_err

def _localized_field(field, lang):
    rv = dict(**field)
    if field.get('field_type') in Field.text_types:
        rv['value'] = rv.setdefault('value', {}).get(lang)
    return rv

def _localize_fields(data, lang):
    for field, value in data.items():
        if field=='data':
            for key, v in value.items():
                if key=='fields':
                    for field in v:
                        if 'value' not in field:
                            continue
                        if field.get('field_type') in Field.text_types:
                            field['value'] = {lang: field['value']}

class Mismatch(Exception):
    pass

def validatekey(record, key, validkeys, ordered_dict=False, strict_keys=False,
               ordered_dict_key='name'):
    # strict_keys: non-existing key raises error

    if len(validkeys)==0 :
        # this is the root of the map, we're trying key directly on the record
        try:
            getattr(record, key)
            return True
        except AttributeError:
            raise Mismatch(f'Invalid attribute: {key}')

    # From here on we're testing keys on JSON columns

    # the first key maps to the record's base field itself
    leaf = field = getattr(record, validkeys[0])

    # validkeys map to values within JSON fields, that are conventionally all
    # encapsulated by a root object {} in this application.

    # getting to the leaf
    for k in validkeys[1:]:
        leaf = leaf[k]

    # test if the new key is valid with the resolved leaf
    try:
        if ordered_dict:
            try:
                return [index for index,l in enumerate(leaf)
                        if l.get(ordered_dict_key)==key][0]
            except IndexError:
                raise KeyError
        else:
            leaf = leaf[key]
            return True
    except TypeError:
        # the type of the field is not consistent with the key
        raise Mismatch('Invalid key')
    except KeyError:
        # the key doesn't exist (yet) in the structure, but usage is
        # consistent with the object's type.
        if not strict_keys:
            # non-existing keys are allowed.
            # return None to signal that it's the case here.
            return

        # if strict_key, raise: only existing keys and indices are allowed
        raise Mismatch('Non-existing key')


def appendobj(record, keymap, obj):
    # first get the base field
    leaf = field = getattr(record, keymap[0])
    # then, navigate to the last item right before the key
    for k in keymap[1:]:
        leaf = leaf[k]
    leaf.append(obj)


def setval(record, keymap, key, value):
    if len(keymap)==1 and key is None:
        # an empty key with a single key in keymap means that this is a direct
        # record's field being set
        try:
            setattr(record, keymap[0], value)
        except:
            raise Mismatch(f'Inconsistent or non-existing attribute')
        return
    # first get the base field
    leaf = field = getattr(record, keymap[0])
    if key is None:
        # if no key was passed, the last item in the keymap is the key
        last_item =  -1
        key = keymap[-1]
    else:
        last_item = len(keymap)
    # navigate to the item before last
    for k in keymap[1:last_item]:
        leaf = leaf[k]
    # then set the value
    leaf[key] = value

def patch_record(record, data, keymap=None, ordered_dict_key='name'):
    if keymap is None:
        keymap = []
    not_strict = False
    objlist = False
    try:
        # First, try to treat data as a dict.
        for k,v in data.items():
            # since it went through, assume data is a dict.
            # verify that key is valid on existing record.
            # validatekey will raise an error on an invalid key (e.g. key does
            # not exist as a base field on the record)
            valid = validatekey(
                record, k, validkeys=keymap, strict_keys=not_strict)
            if valid is None:
                # the special case where the key did not exist directly on the
                # record, but method of access was consistent with the data
                # type it was tested on. This would be indicative that we're
                # setting a field somewhere inside a JSON column.
                # Set the value on the new key.
                setval(record, keymap, k, v)
                # go to next data item
                continue
            # the key exists in the record
            keymap.append(k)
            # recursively try to assign the value to it
            patch_record(record, v, keymap)
            # the value has now been assigned, pop the key
            keymap.pop(-1)
    except AttributeError: # data is not a dict
        try: # Second, try to treat data as a string or a list of named objects.

            # is it a string?
            if type(data) is str:
                # if this is a string, just assign and end right here
                setval(record, keymap, None, data)
                return

            # try iterating
            for obj in data:
                # if it went through, it's a listlike structure
                try:
                    # is this an ordered list of dicts?
                    key = obj[ordered_dict_key]
                except KeyError:
                    # access method was consistent with dict type, but the key
                    # was not found.
                    # raise because it violates the convention that any dict
                    # in a list must have an identifying key (defaults to
                    # 'name').
                    raise Mismatch('Missing identifier key in object')
                # turn on the object list behavior flag
                objlist = True
                # find the index of the object in current field
                index = validatekey(
                    record, key, validkeys=keymap, strict_keys=not_strict,
                    ordered_dict=True)
                if index is None:
                    # obj did not exist inside the list, add it
                    appendobj(record, keymap, obj)
                    # go to next item in list
                    continue
                # index exists
                keymap.append(index)
                # recursive patching
                patch_record(record, obj, keymap)
                # value has been assigned, pop and move on.
                keymap.pop(-1)
            # iteration on object list completed properly, turn off the flag.
            objlist = False
        except TypeError: # not a list of named objects
            mixing_error = ('Badly formed data. Probable mix of objects '
                            'with simpler data types')
            if objlist is True:
                # the previous list iteration did not complete properly,
                # maybe because one item in the sequence was not an object.
                raise Mismatch(mixing_error)
            try:
                # should raise a TypeError error if not a list, that's fine.
                for item in data:
                    try:
                        # should raise a TypeError, as there shouldn't be any
                        # object included as part of the list.
                        item['key']
                    except TypeError:
                        # good, skip to next item.
                       continue
                    except KeyError:
                        # not good, because it implies that even though 'key'
                        # was not found item is still a dict.
                        # let slip toward the Mismatch error.
                        pass
                    # badly formed data.
                    raise Mismatch(mixing_error)
            except TypeError:
                pass
            # Finally, treat data as a simple value or list of values.
            setval(record, keymap, None, data)


def _merge_localized_data(old, new, fields, lang):
    for field in fields:
        path = field.split('.')
        oldval = old
        newval = new
        for p in path[:-1]:
            oldval = oldval.setdefault(p, {})
            newval = newval.setdefault(p, {})
        oldval.setdefault(path[-1], {})[lang] = newval.get(path[-1])
    return oldval


def localize_data(data, fields, lang):
    """
    add a language key to the specified fields.
    """
    rv = deepcopy(data)
    for field in fields:
        path = field.split('.')
        val = rv
        for p in path[:-1]:
            val = val.setdefault(p, {})
        # reset last value to a localized dict
        val[path[-1]] = {lang: val.get(path[-1])}
    return rv

def delocalize_data(data, fields, lang):
    """
    remove language key from specified fields.
    """
    rv = deepcopy(data)
    for field in fields:
        # create a map for each localized field
        path = field.split('.')
        # resolve the value of the item before last on the map
        # i.e. before the item containing the localized data
        val = rv
        for i, p in enumerate(path):
        #for p in path[:-1]:
            if i==len(path)-1:
                break
            val = val.setdefault(p, {})
        # replace the value of the last item by its localized version
        val[path[-1]] = val.get(path[-1], {}).get(lang)
    return rv


def run_or_abort(fnc, code=None, msg=None):
    # api - util
    """
    Receive and call a function that delegates to a service. If a ServiceError is raised,
    reraises it as a JSON response.
    """
    try:
        return fnc()
    except srv_err.ServiceError as e:
        code = code or e.code
        msg_dict = {'message': msg} if msg else srv_err.to_dict(e)
    except:
        code = code or 400
        msg_dict = {'message': msg if msg else 'Malformed or missing data'}
    json_abort(code, msg_dict)


class StripeContext:

    def __init__(self):
        self.stripe = stripe
        self.handlers = {}

    def register_handler(self, error_type, handler):
        self.handlers[error_type] = handler

    def __enter__(self):
        return self

    def __exit__(self, e_type, e_value, traceback):
        if e_type:
            # first rollback db session
            db.session.rollback()
            if self.handlers.get(e_type):
                self.handlers[e_type](e_value, traceback)
            elif e_type==stripe.error.CardError:
                msg = err.get('message', 'Problem with payment method')
                code = e_value.http_status
                json_abort(code, {'error': msg})
            #elif e_type==stripe.error.RateLimitError:
            #elif e_type==stripe.error.InvalidRequestError:
            #elif e_type==stripe.error.AuthenticationError:
            #elif e_type==stripe.error.APIConnectionError:
            #elif e_type==stripe.error.StripeError:
            else:
                raise
                json_abort(400, {'error': 'Could not process request'})
