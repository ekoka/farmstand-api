# coding=utf8
import re
import copy
import sys
from decimal import Decimal

EXTRA_PROPERTIES_RAISE = 'raise_error'
EXTRA_PROPERTIES_EXCLUDE = 'exclude'
EXTRA_PROPERTIES_IGNORE = 'ignore'
EXTRA_PROPERTIES_DEFAULT = EXTRA_PROPERTIES_RAISE

py3 = sys.version_info[0] == 3

STR_TYPES = (unicode, str,) if py3 else (unicode, basestring,)
INT_TYPES = (int,) if py3 else (int, long)
NUMBER_TYPES = (int, Decimal) if py3 else (int, long, Decimal)
BOOL_TYPES = (bool,) #if py3 else (bool,)

# markers
_init = object() # mark a start
_missing = object() # mark an unset or missing field


def isobjectschema(schema):
    return isinstance(schema, dict) and\
            ("properties" in schema or schema.get("type") == "object")

def isarrayschema(schema):
    return isinstance(schema, dict) and\
            ("items" in schema or schema.get("type") == "array")

def make_path_string(path, skip_root=True):
    if skip_root:
        path = path[1:]
    path_string = ''
    for f in path:
        if isinstance(f, int) and f >= 0:
            f = '[{f}]'.format(f=f)
        else:
            f = '.{f}'.format(f=f)
        path_string += f
    return path_string.strip('.')

def validation_error(message=None, value=None, path=None, **kw):
    fieldname = None
    try:
        fieldname = make_path_string(path, skip_root=True)
        #local_dict['path'] = fieldname
    except:
        pass

    if message is None:
        message = u"Invalid value or type at field '{fieldname}': '{value}'."
    message = message.format(**locals())

    raise ValidationError(message=message, value=value, fieldname=fieldname, 
                          path=path, **kw)

class SchemaError(Exception):
    pass

def validate(*a, **kw):
    v = Validator(*a, **kw)
    return v.validate()

class ValidationError(Exception):

    def __init__(self, message, value=None, fieldname=None, **kw):
        super(ValidationError, self).__init__(message)
        self.value = value
        self.fieldname = fieldname
        for k,v in kw.iteritems():
            setattr(self, k, v)

    @property
    def msg(self):
        return self.args[0]

    #def __str__(self):
    #    path = ' @ %s' % '['.join(map(repr, self.path)) \
    #        if self.path else ''
    #    return Exception.__str__(self) + path

class Validator(object):
    def __init__(self, data, schema, formatters=None, modifiers=None,
                 validators=None, extra_properties_default=None,
                 required_default=False, allowblank_default=False,
                 allownull_default=True):
        self.original_data = data
        self.data = copy.deepcopy(data)
        self.schema = schema
        self.modifiers = modifiers
        self.validators = validators
        

        self.extra_properties_default = extra_properties_default or\
                                        EXTRA_PROPERTIES_DEFAULT
        self.required_default = required_default
        self.allowblank_default = allowblank_default
        self.allownull_default = allownull_default
    
    def validate(self, value=_init, schema=_init, fieldname=_init, path=_init):
        if schema is _init:
            schema = self.schema
        if value is _init:
            value = self.data
        if fieldname is _init:
            fieldname = '__root__'
        if path is _init:
            path=[]

        path.append(fieldname)

        if isobjectschema(schema):
            value = self.validate_object(data_object=value, schema=schema,
                                         fieldname=fieldname, path=path)
        elif isarrayschema(schema):
            value = self.validate_array(data_array=value, schema=schema,
                                        fieldname=fieldname, path=path)
        else:
            value = self.validate_value(value=value, schema=schema, 
                                        fieldname=fieldname, path=path)
        path.pop()

        return value

    def handle_extra_properties(self, data_object, schema):
        extra = schema.get('extra_properties', self.extra_properties_default)
        if extra == EXTRA_PROPERTIES_IGNORE:
            return

        diff = set(data_object) - set(schema.get('properties', {}))
        if extra == EXTRA_PROPERTIES_RAISE:
            if diff:
            #TODO
                validation_error('Extra properties in data.')
        elif extra == EXTRA_PROPERTIES_EXCLUDE:
            [data_object.pop(x) for x in diff]
        else:
            msg = u'{extra} is not a valid setting '\
                  u'for extra_properties.'.format(extra=extra)
            raise SchemaError(msg)

    def validate_object(self, data_object, schema, fieldname, path):
        special_rules = ['required', 'allownull']
        data_object = self.validate_special(
            rules=special_rules, value=data_object, schema=schema,
            fieldname=fieldname, path=path)

        if data_object is _missing:
            return data_object

        if not isinstance(data_object, dict):
            validation_error(u'{fieldname} should be an object.', path=path)
        self.handle_extra_properties(data_object=data_object, schema=schema)

        for p, s in schema["properties"].iteritems():
            # distinguishing between missing and explicit None values
            value = data_object.get(p, _missing)
            value = self.validate(value=value, schema=s,
                                  fieldname=p, path=path)
            if value is not _missing:
                data_object[p] = value
        return data_object

    def validate_array(self, data_array, schema, fieldname=None, path=None):
        special_rules = ['required']
        data_array = self.validate_special(
            rules=special_rules, value=data_array, schema=schema,
            fieldname=fieldname, path=path)

        if data_array is _missing:
            return data_array

        if not isinstance(data_array, (list, tuple, set)):
            validation_error(u'{fieldname} should be an array.', path=path)

        items_schema = schema.get('items')
        if isinstance(items_schema, dict):
            new = [self.validate(value=value, schema=items_schema,
                                 fieldname=index, path=path)
                   for index, value in enumerate(data_array)]
            [data_array[index] for index, data in enumerate(new)]
        elif isinstance(items_schema, list):
            for i, item_schema in enumerate(items_schema):
                #field = "[{i}]".format(f=fieldname, i=index)
                data_array[i] = self.validate(data_array[i], item_schema,
                                              fieldname=i, path=path)
            additional_schema = schema.get('additional_items')
            if additional_schema:
                while True:
                    i += 1
                    try:
                        data_array[i] = self.validate(value=data_array[i],
                                                      schema=additional_schema,
                                                      fieldname=i, 
                                                      path=path)
                    except IndexError:
                        break
        return data_array


    def validate_special(self, rules, value, schema, fieldname=None, 
                         path=None):
        for r in rules:
            if not r in schema:
                schema[r] = getattr(self, r + '_default')
            fnc_name = "validate_" + r
            fnc = getattr(self, fnc_name)
            value = fnc(value=value, schema=schema, fieldname=fieldname,
                        path=path, data=self.data)
        return value

    def validate_value(self, value, schema, fieldname=None, path=None):
        # first let's handle the special cases
        special_rules = ['required', 'allowblank', 'allownull']
        value = self.validate_special(
            rules=special_rules, value=value, schema=schema, 
            fieldname=fieldname, path=path)

        if value is _missing:
            return value


        for r in set(schema)-set(special_rules)-{'formaters', 'validators'}:
            fnc_name = "validate_" + r
            fnc = getattr(self, fnc_name)
            value = fnc(value=value, schema=schema, fieldname=fieldname, 
                        path=path, data=self.data)

        value = self.process_validators(value=value, schema=schema, 
                                        fieldname=fieldname, path=path)
        return value 

    def process_validators(self, value, schema, fieldname=None, path=None):
        for fnc in schema.get('validators', []):
            if isinstance(fnc, basestring):
                fnc_name = "validate_" + fnc
                fnc = getattr(self, fnc_name)
            
            value = fnc(value=value, schema=schema, fieldname=fieldname, 
                        path=path, data=self.data)

        return value

    def validate_required (self, value, schema, fieldname=None, path=None,
                           data=None):
        if value is _missing: 
            if schema['required']:
                validation_error(u'{fieldname} is required.', path=path, 
                                 value=u'<undefined>')
        return value

    def validate_allowblank(self, value, schema, fieldname=None, path=None, 
                       data=None):
        if value or schema['allowblank'] is True:
            return value

        # so far only strings can be blank
        if not isinstance(value, STR_TYPES):
            return value

        value = value.strip() #TODO: this should be a separate processor
        if value=='':
            validation_error(
                u"'{fieldname}' field cannot be blank.", path=path, value=value)
        return value

    def validate_allownull(self, value, schema, fieldname=None, path=None,
                      data=None):
        if value or schema['allownull'] is True:
            return value
        
        if value is None:
            validation_error(u"'{fieldname}' field cannot be null.",
                             path=path, value=value)
        return value

    def validate_type(self, value, schema, fieldname=None, path=None, 
                      data=None):
        types = [schema['type']] if isinstance(schema['type'], STR_TYPES) \
                                  else list(schema['type'])
        #exc = []
        for t in types:
            fnc_name = "validate_type_" + str(t)
            fnc = getattr(self, fnc_name)
            if fnc is None:
                raise SchemaError('Unsupported type: {t}'.format(t=t))
            try:
                value = fnc(value=value, type_=t, fieldname=fieldname,
                            path=path, data=data)
                return value
            except Exception as e:
                #exc.append(e)
                pass
        msg = u"Invalid type at field '{fieldname}' with value '{value}'."
        validation_error(msg, value=value, path=path)


    def validate_type_int(self, *a, **kw):
        #TODO: Note that booleans validate as integers
        return self._validate_type(INT_TYPES, *a, **kw)
    validate_type_integer = validate_type_int

    def validate_type_str(self, *a, **kw):
        return self._validate_type(STR_TYPES, *a, **kw)
    validate_type_string = validate_type_str

    def validate_type_bool(self, *a, **kw):
        return self._validate_type(BOOL_TYPES, *a, **kw)
    validate_type_boolean = validate_type_bool
    
    def validate_type_number(self, *a, **kw):
        return self._validate_type(NUMBER_TYPES, *a, **kw)
    validate_type_num = validate_type_number

    def _validate_type(self, types, value, type_, fieldname=None, path=None,
                       data=None):
        # None value should be handled separately, so we skip.
        if value is None:
            return value

        # sometimes we want to force the conversion
        # e.g. we want 123 but we get '123'
        if isinstance(type_, Coerce):
            for t in types:
                try:
                    value = t(value)
                    return value
                except ValueError:
                    pass
        elif isinstance(value, types):
            return value
        validation_error(value=value, path=path)

    def validate_pattern(self, value, schema, fieldname=None, path=None, 
                         data=None):
        pattern = schema['pattern']
        try:
            if re.match(pattern, value):
                return value
        except:
            pass
        validation_error(u'{fieldname} doesn\'t seem valid.', value=value,
                         path=path)
        

class Coerce(object):
    def __init__(self, type):
        self.type = type
    def __str__(self):
        return self.type

def coerce(*types):
    return [Coerce(t) for t in types]
