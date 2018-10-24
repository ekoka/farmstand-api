
def parse_keys(multidict):
    rv = {}
    for key, values in multidict.iterlists():
        keys = key.split('.')
        obj = rv
        for index, k in enumerate(keys):
            if len(keys)==index + 1:
                obj[k] = values
                # last iteration
            else:
                obj = obj.setdefault(k, {})
    return rv
