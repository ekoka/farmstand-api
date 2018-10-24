import six
from collections import abc as col_abc
from abc import ABCMeta, abstractmethod, abstractproperty

class Range(metaclass=ABCMeta):

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Range:
            no_start = lambda b: 'start' not in b.__dict__
            no_stop = lambda b: 'stop' not in b.__dict__
            no_step = lambda b: 'step' not in b.__dict__
            for B in C.__mro__:
                return False if no_start(B) or no_stop(B) or no_step(B) else True
        return NotImplemented


#def is_listlike(l):
#    try:
#        len(l)
#        return True
#    except:
#        return False
#
#def is_intlike(value, positive=False, bool_as_int=False):
#    if not bool_as_int: 
#        if value is True or value is False:
#            return False
#    try:
#        [0][value]
#        return True
#    except IndexError:
#        return value>=0 if positive else True
#    except TypeError:
#        return False
#
#def is_iterable(value, exclude_list=False, exclude_tuple=False,
#        exclude_generator=False, exclude_set=False, exclude_dict=True,
#        exclude_str=True, exclude_bytes=True):
#    if exclude_list and is_list(value):
#        return False
#    if exclude_tuple and is_tuple(value):
#        return False
#    if exclude_set and is_set(value):
#        return False
#    if exclude_generator and is_generator(value):
#        return False
#    if exclude_dict and is_dict(value):
#        return False
#    if exclude_str and is_str(value):
#        return False
#    if exclude_bytes and is_bytes(value):
#        return False
#    return True
#
#def is_list(value):
#    return hasattr(value, '__iter__') and hasattr(value, 'reverse')
#
#def is_tuple(value):
#    return (hasattr(value, '__iter__') and not hasattr(value, 'append')
#            and not hasattr('capitalize'))
#
#def is_set(value):
#    return hasattr(value, '__iter__') and hasattr(value, 'union')
#
#def is_generator(value):
#    return hasattr(value, '__iter__') and hasattr(value, 'close')
#
#def is_dict(value):
#    return hasattr(value, '__iter__') and hasattr(value, 'get')
#
#def is_str(value):
#    return hasattr(value, '__iter__') and hasattr(value, 'encode')
#
#def is_bytes(value):
#    return hasattr(value, '__iter__') and hasattr(value, 'decode')
#
#def is_boolean(value, int_as_bool=False):
#    if not int_as_bool:
#        if value is 1 or value is 0:
#            return False
#    return value in (True, False)
#
#def to_str(value):
#    if is_str(value):
#        return value
#    if is_bytestring(value):
#        return value.decode('utf8')
#    return str(value)
#
#def is_numberlike(value, exclude_decimal=False):
#    try:
#        0 + value
#    except TypeError:
#        return False
#    if exclude_decimal and hasattr(value * 0, 'is_integer'):
#        return False
#    return True
