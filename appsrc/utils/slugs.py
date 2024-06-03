import re

import re
import unicodedata

__version__ = '0.0.1'


def _slugify(string):

    """
    Slugify a unicode string.

    Example:

        >>> slugify(u"Héllø Wörld")
        u"hello-world"

    """

    string = unicodedata.normalize('NFKD', string)#.encode('ascii', 'ignore')
    return re.sub(
        r'[-\s]+', 
        '-',
        str(re.sub(r'[^\w\s-]', '', string).strip().lower())
    )

def slugify(text):
    text = re.sub(r'&', 'and', text)
    return _slugify(text).lower()
