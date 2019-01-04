from ..fields import name, number, description, available

schema = {
    "name": "generic",
    "schema": {
        "fields": [
            {"field": name, "display": True, "searchable": True},
            {"field": number, "display": True, "searchable": True},
            {"field": available, "display": True, "searchable": False},
            {"field": description, "display": True, "searchable": True},
        ]
    }
}
