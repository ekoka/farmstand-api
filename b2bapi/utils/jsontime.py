from datetime import datetime

def str2date(datestr, frm=None):
    datestr = datestr.strip()[:10]
    if frm is None:
        frm = '%Y-%m-%d'
    return datetime.strptime(datestr, frm).date()

def str2time(timestr, frm=None):
    if frm is None:
        frm = '%H:%M'
    if frm == '%H:%M':
        timestr = timestr.strip()[:5]
    return datetime.strptime(timestr, frm).time()
    #except TypeError, ValueError:
    #    return None

def str2datetime(datetimestr, frm=None):
    datetimestr = datetimestr.strip()[:16]
    if frm is None:
        frm = '%Y-%m-%dT%H:%M'
    return datetime.strptime(datetimestr, frm)
