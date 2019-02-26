from flask import Blueprint

bp = blueprint = Blueprint('api', __name__, url_prefix='/api')


from . import _route
from . import auth
from . import filters
from . import domains
from . import index
from . import products
from . import images
from . import accounts
#from . import inquiries
from . import quotations
from . import product_fields
from . import product_types
from . import billing
from .public import (
    products as public_product, 
    root as public_root,
    #inquiries as public_inquiries,
    quotations as public_quotations,
)
