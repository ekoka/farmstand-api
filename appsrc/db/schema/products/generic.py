from ..fields import name, number, description, available, visible

schema = {
    "name": "generic",
    "schema": {
        "fields": [
            {"field": name, "display": True, "searchable": True,
             'localized': True},
            #},
            {"field": description, "display": True, "searchable": True,
             'localized': True},
            #},
            {"field": number, "display": True, "searchable": True},
            {"field": available, "display": True, "searchable": False},
            {"field": visible, "display": False, "searchable": False},
        ]
    }
}
