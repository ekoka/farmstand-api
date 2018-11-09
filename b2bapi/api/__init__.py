import functools
import simplejson as json

from werkzeug.datastructures import MultiDict
from flask import Blueprint, current_app, request, g, url_for, redirect, abort

bp = blueprint = Blueprint('api', __name__, url_prefix='/api')


from . import _route
from . import auth
from . import filters
from . import tenants
from . import index
from . import products
from . import images
from . import accounts
from . import inquiries
from .public import (
    products as public_product, 
    root as public_root,
    inquiries as public_inquiries,
)
