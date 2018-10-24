import uuid

def clean_uuid(value, hyphenated=False):
    # the normalize option is useful to avoid inconsistencies that may arise
    # as a result of having UUIDs both with and without hyphens
    try:
        rv = uuid.UUID(str(value), version=4)
        return str(rv) if hyphenated else rv.hex
    except ValueError:
        pass
