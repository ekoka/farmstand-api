from functools import singledispatch
import uuid
import datetime
import simplejson as json
from flask import Response

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

def str2date(datestr, frm=None):
    datestr = datestr.strip()[:10]
    if frm is None:
        frm = '%Y-%m-%d'
    return datetime.datetime.strptime(datestr, frm).date()

def str2time(timestr, frm=None):
    if frm is None:
        frm = '%H:%M'
    if frm == '%H:%M':
        timestr = timestr.strip()[:5]
    return datetime.datetime.strptime(timestr, frm).time()

def str2datetime(datetimestr, frm=None):
    datetimestr = datetimestr.strip()[:16]
    if frm is None:
        frm = '%Y-%m-%dT%H:%M'
    return datetime.datetime.strptime(datetimestr, frm)

def json_response(data, status=None, headers=None, json_dumps=True):
    """
    See also json_response_wrapper in cachetools
    """
    json_dumps = True
    if json_dumps:
        # for when data needs to be converted to json
        data = json.dumps(data, use_decimal=True, default=json_serialize)
    return Response(
        data, mimetype='application/json',
        status=status, headers=headers)
