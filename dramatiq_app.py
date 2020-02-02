import dramatiq
from b2bapi import settings as config
from b2bapi import make_app
from b2bapi import scheduled
# the connection between dramatiq and the Flask app happens in `make_app`
app = make_app(config)
