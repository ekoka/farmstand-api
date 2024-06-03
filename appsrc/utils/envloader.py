from os import environ as env
from simplejson import loads as jsonloads

BOOL_VALUES = ('true', 'false', 'yes', 'no')
NONE_VALUES = ('none', 'nil', 'null', '')

missing = object()

def num(cnfkey, default=None, required=True):
    cnfval = confvalue(cnfkey, required)
    if cnfval is missing:
        return default
    if cnfval is None or cnfval.lower() in NONE_VALUES:
         return None
    try:
        return int(cnfval)
    except ValueError:
        pass
    try:
        return float(cnfval)
    except ValueError:
        pass
    raise TypeError(
        'Expected numerical for `%s`. Got %s' % (cnfkey, type(cnfkey))
    )

def string(cnfkey, default=None, required=True):
    cnfval = confvalue(cnfkey, required)
    if cnfval is missing:
        return default
    if cnfval is None or cnfval.lower() in NONE_VALUES:
         return None
    return cnfval

def binstring(cnfkey, default=None, required=True):
    """
    This function is useful mostly when a string with possible escaped chars
    is set as environment variable (e.g. a secret key). In the Python runtime
    that string will be escaped. It needs to be un-escaped to be used as
    intended.
    See:
    https://stackoverflow.com/questions/14820429/how-do-i-decodestring-escape-in-python-3
    https://stackoverflow.com/questions/1885181/how-to-un-escape-a-backslash-escaped-string
    https://stackoverflow.com/questions/4020539/process-escape-sequences-in-a-string-in-python
    """
    cnfval = string(cnfkey, default, required).encode('ascii')
    return cnfval.decode('unicode_escape').encode('latin1')

def boolean(cnfkey, default=None, required=True):
    cnfval = confvalue(cnfkey, required)
    if cnfval is missing:
        return default
    if cnfval is None or cnfval.lower() in NONE_VALUES:
         return None
    if cnfval.lower() in BOOL_VALUES:
        return True if cnfval.lower() in ('true', 'yes') else False
    raise TypeError(
        'Expected boolean for `%s`. Got %s' % (cnfkey, type(cnfkey))
    )

def json(cnfkey, default=None, required=True):
    cnfval = confvalue(cnfkey, required)
    if cnfval is missing:
        return default
    if cnfval is None or cnfval.lower() in NONE_VALUES:
         return None
    try:
        return jsonloads(cnfval)
    except:
        pass
    raise TypeError(
        'Expected valid JSON string for `%s`. Got \n %s' % (cnfkey, cnfval)
    )

def confvalue(cnfkey, required):
    cnfval = env.get(cnfkey, missing)
    if cnfval is missing:
        if required:
            raise KeyError(
                "'{cnfkey}' expected in environment.".format(cnfkey=cnfkey)
            )
        return missing
    conftype = type(cnfval)
    try:
        assert conftype is str
        return cnfval
    except AssertionError:
       "'str' type expected for configuration key. Got '{conftype}'.".format(
            conftype=conftype
        )

class namespace:
    def __init__(self, prefix):
        self.prefix = prefix

    def __getattr__(self, name):
        proxy_func = globals()[name]
        def wrapper(*a, **kw):
            a = [*a]
            try:
                cnfkey = a[0]
            except IndexError:
                cnfkey = kw.pop('cnfkey')
            a[0] = f"{self.prefix}_{cnfkey}"
            return proxy_func(*a, **kw)
        return wrapper
