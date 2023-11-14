from ..utils import envloader

# just making it explicitly clear that we're simply proxying for other modules in config
env = envloader

def get_upper_keys(keys):
    """
    Return only uppercase keys.
    """
    return [k for k in keys if k.isupper()]
