from functools import singledispatch
import uuid
import datetime

@singledispatch
def json_serialize(value):
    """ this is a generic function """
    return str(value)

@json_serialize.register(uuid.UUID)
def to_string(value):
    return value.hex

@json_serialize.register(datetime.datetime)
def to_string(value):
    return value.isoformat()
