from copy import deepcopy

from b2bapi.db.models.meta import Field

"""
NOTE: There's not yet a clear understanding of how values in lists should be 
handled.
Some possibilities:
    - just assign the entire list to the specified key/attribute
    - assign a flag as the first item in the list that specifies how it should
    be handled (e.g. named dict, etc).
    - traverse the list and for each item determine if the existing list has a 
    corresponding type (how and what to do when it doesn't, sounds complicated).
Some consideration
------------------
Changing values atomically in a list would be too complicated if the indices of the 
new items determine their position in the target. Thus a way to specify the position
of the item would be ideal. Only a dict can allow this kind of representation natively.
So the list's data would be specified as if it's a dict.

    {'data': {
        'somelist': {
            0: 'foo',  # replace the value at 0 by 'foo'
            3: 'bar'    # replace the value at 3 by 'bar'
        }
    }}

What happens if the specified index doesn't exist in the list?

----
A sounder approach:
    - the use of list is standardized around two groups of data types: the
    first includes only dicts, the other is made up of the remaining common 
    types, that is, simple types (bool, number, string) and lists.
    - a dict cannot be placed in a list of items and items cannot be in a 
    list of dicts.
    - this implies that if a list contains a dict, all other items of that
    list must also be dicts.
    - a list can thus only keep items of a single group at a time.
    - if a structure is needed to keep data of varying types, a dict can be
    used to that effect.
    - all dicts in lists must have an identifying key (default to 'name' if
    not configured), that is, only named dicts can be stored inside lists.
    - changes to dicts in a list are made atomically.
    - whereas the data tree sprouting from a list of simple items is just
    assigned to the attribute as a whole.
    - although lists can also be directly nested in other lists, it would
    probably be advisable to use an alternative structure, unless really
    necesary. 
    This is because, since list of simple are simply assigned to an attribute,
    if an inner list happens to have a more complex structure (e.g. a dict in
    a list in a list), it will simply be part of the assigned "chunk" of data.
    It will not be possible to atomically update that structure, since there
    won't be a way to specify the positioning of the child list and thus to
    navigate to any of its children. So use direct nested lists with a caveat.

"""

def _localized_product_field(field, lang):
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

def validatekey(record, key, validkeys, ordered_dict=False, strict_keys=False):
    # named_index: indicates that the data is a dict inside a list
    # and should be identified with a field identified by the named_index.

    # strict_keys: non-existing key raises error

    if len(validkeys)==0 :
        # this is the root of the map, try key directly on record
        try:
            getattr(record, key)
            return True
        except AttributeError:
            raise Mismatch(f'Invalid attribute: {key}')

    # the first key maps to the field itself
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
                        if l.get('name')==key][0]
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

        # in case only existing keys and indices are allowed
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

def patch_record(record, data, keymap=None):

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
                # the special case where the key did not exist on the part of
                # the record that it was tested on, but access method was
                # consistent with the data type (e.g. a JSON object's field).
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
                    # is it a sequence of dict?
                    key = obj['name']
                except KeyError:
                    # dict's key access method was recognized, but the key was
                    # not found.
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


def _localize_data(data, fields, lang):
    rv = deepcopy(data) 
    for field in fields: 
        path = field.split('.')
        val = rv
        for p in path[:-1]:
            val = val.setdefault(p, {})
        # reset last value to a localized dict
        val[path[-1]] = {lang: val.get(path[-1])}
    return rv
    
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
            
def _delocalize_data(data, fields, lang):
    rv = deepcopy(data)
    for field in fields: 
        # create a map for each localized field
        path = field.split('.')
        # resolve the value of the item before last on the map 
        # i.e. before the item containing the localized data
        val = rv
        for p in path[:-1]:
            val = val.setdefault(p, {})
        # replace the value of the last item by its localized version
        val[path[-1]] = val.get(path[-1], {}).get(lang)
    return rv
