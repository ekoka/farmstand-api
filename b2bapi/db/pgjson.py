import functools
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.ext.mutable import Mutable

"""
This is a simple implementation of a Mutable JSON structure. It may be a rudimentary approach for simple scenarios. 

My first approach was to make both wrapping and embedded objects mutable, but I got nowhere satisfactory. My embedded objects would issue `changed()` triggers that were not being acknowledged at the ORM level.

This implementation instead only relies on the main wrapper object (aka `root_instance` in the code) to speak to the ORM. Embedded objects proxy to that "root" object to also talk to the ORM.

You'll also notice that we don't care about making added structures mutable as well.
The premise is that we're working with JSON structures that presumably come from the db and that have been loaded into their Python equivalent, namely dict, list, and basic types. In that scenario we only need to keep track of the starting value of the attribute. Any modification to that initial attribute should trigger a 'changed' state. Thus, there's no need to worry about tracking structures that have been added after (since adding them was itself already a trigger). That's why we don't care about applying this "mutabilizing" step to new structures. Upon being committed to the db and later reloaded, they'll go through this as well.
"""

def broadcast_changes(cls):
    mutating_methods = [
        '__delitem__', 
        '__setitem__', 
        '__setslice__',
        '__delslice__',
        '__iadd__',
        'append', 
        'pop', 
        'setdefault',
        'update', 
        'popitem', 
        'clear',
        'extend',
        'insert',
        'remove',
        'clear',
        'sort',
        'reverse',
    ]

    def enable_broadcasting(m):
        @functools.wraps(m)
        def wrapper(*a, **kw):
            self = a[0]
            rv = m(*a, **kw)
            self.changed()
            return rv
        return wrapper

    for m in mutating_methods:
        if hasattr(cls, m):
            setattr(cls, m, enable_broadcasting(getattr(cls, m)))

    return cls

class MutableContainer(Mutable):
    def __init__(self, root_instance=None):
        # `root_instance` is the parent object. The one that's directly
        # connected with the attribute at the ORM level and consequently also
        # the one that's listened to for changes.

        # provide a reference to it to each descendant.
        if root_instance is None:
           root_instance = self
        self.root_instance = root_instance

    def changed(self):
        # Only root can speak to the ORM, embedded instances thus proxy to it.
        if self.root_instance is self:
            return Mutable.changed(self)
        return self.root_instance.changed()

    @classmethod
    def coerce(cls, key, value):
        return cls.json_value(value)

    @classmethod
    def json_value(cls, value, root_instance=None):
        if isinstance(value, dict):
            return MutableDict(value, root_instance)

        if isinstance(value, list):
            return MutableList(value, root_instance)

        return value

@broadcast_changes
class MutableDict(dict, MutableContainer):
    def __init__(self, value, root_instance=None):
        MutableContainer.__init__(self, root_instance)
        dict.__init__(self, ((k, MutableContainer.json_value(
            v, self.root_instance)) for k,v in value.items()))

@broadcast_changes
class MutableList(list, MutableContainer):
    def __init__(self, value, root_instance=None):
        MutableContainer.__init__(self, root_instance)
        list.__init__(self, (MutableContainer.json_value(
            v, self.root_instance) for v in value))


# our mutable JSON
JSON = MutableContainer.as_mutable(pg.JSON)
JSONB = MutableContainer.as_mutable(pg.JSONB)

