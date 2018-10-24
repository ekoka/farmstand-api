import string
import random

def randomstr(n, chars=None, ucase=True, lcase=True, digits=True):
    """
    Usage: 

    - return string of 6 random characters made up of lower and upper ascii
    letters and digits.

        >>> randomstr(6)

    - return string of 6 random characters made up of only lower letters and 
    digits.

        >>> randomstr(6, ucase=False)

    - 
    """
    if chars is None:
        if ucase is True:
            ucase = string.ascii_uppercase
        elif ucase in (False, None):
            ucase = ''

        if lcase is True:
            lcase = string.ascii_lowercase
        elif lcase in (False, None):
            lcase = ''

        if digits is True:
            digits = string.digits
        elif digits in (False, None):
            digits = ''

        chars = ucase + lcase + digits 

    s = random.SystemRandom()
    return ''.join(s.choice(chars) for _ in range(n))
