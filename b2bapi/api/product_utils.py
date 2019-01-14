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
            return [index for index,l in enumerate(leaf) 
                    if l.get('name')==key][0]
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

    try:
        # First, try to treat data as a dict.
        for k,v in data.items():
            # since it went through, assume data is a dict
            # verify that the key is valid on record
            try:
                valid = validatekey(
                    record, k, validkeys=keymap, strict_keys=not_strict)
            except Mismatch:
                app.logger.info('Mismatch raised')
                # abort the entire operation
                raise TypeError()

            if valid is None:
                # the key did not exist but was consistent with the data type.
                # set the value on the new key
                setval(record, keymap, k, v)
                # go to next data item
                continue

            # the key exists
            keymap.append(k)
            # recursively try to assign the value to it 
            patch_record(record, v, keymap)
            # assuming the value has been assigned, pop the key
            keymap.pop(-1)
    except AttributeError: # not a dict
        try:
            # Second, try to treat data as a list of named objects.
            for obj in data:
                key = obj['name']
                    
                try:
                    # find the index of the object in current field 
                    index = validatekey(
                        record, key, validkeys=keymap, strict_keys=not_strict,
                        ordered_dict=True)
                except Mismatch:
                    # abort the entire operation
                    raise TypeError()

                if index is None:
                    # obj did not exist inside the list, add it
                    appendobj(record, keymap, obj)
                    # go to next item in list
                    continue

                # index exists
                keymap.append(index)
                patch_record(record, obj, keymap)
                keymap.pop(-1)
        except (TypeError, KeyError): # not a list of named objects
            # Finally, treat data as a simple value.
            setval(record, keymap, None, data)
