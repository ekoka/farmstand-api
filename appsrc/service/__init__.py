from flask import Blueprint

bp = blueprint = Blueprint('api', __name__, url_prefix='/api')

from .routes import (
    accounts,
    auth,
    billing,
    domains,
    groups,
    images,
    index,
    inquiries,
    product_fields,
    product_types,
    products,
)
from .routes.public import (
    domains as public_domains,
    products as public_products,
    root as public_root,
    inquiries as public_inquiries,
)

from . import auth
from . import groups
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
    inquiries as public_inquiries,
    #quotations as public_quotations,
    domains as public_domains,
)
