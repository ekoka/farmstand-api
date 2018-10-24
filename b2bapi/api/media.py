import uuid
import simplejson as json

from flask import redirect, g, current_app as app, url_for

from b2bapi.db import db
from b2bapi.db.models.products import Product
from b2bapi.db.models.media import Media

from ._route import route

#@route('/media', expects_files=True) # multiple files
@route('/media', expects_data=True, expects_file=True)
def post_media(data, file):
    pass

