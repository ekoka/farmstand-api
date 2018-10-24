from datetime import datetime
import pytz

def fromutc(dt, tz, naive=True):
    if isinstance(tz, basestring):
        tz = pytz.timezone(tz)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    rv = dt.astimezone(tz)
    if naive:
        return rv.replace(tzinfo=None)
    return rv

def toutc(dt, default_tz=None, naive=True):
    if default_tz is None:
        default_tz = pytz.utc
    elif isinstance(default_tz, basestring):
        default_tz = pytz.timezone(default_tz)

    if dt.tzinfo is None:
        dt = default_tz.localize(dt)
    rv = dt.astimezone(pytz.utc)
    if naive:
        return rv.replace(tzinfo=None)
    return rv
        
    
    
