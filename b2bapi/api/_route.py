import functools
import requests
from flask import g, request, url_for, current_app as app, jsonify, abort
from werkzeug import exceptions as werk_exc, Response
from werkzeug.datastructures import MultiDict
import re 
import jwt

from . import blueprint as bp
from b2bapi.db import db
from b2bapi.db.models.accounts import Account
from b2bapi.db.models.domains import Domain, DomainAccount
from b2bapi.utils.cachelib import json_response
from b2bapi.utils import abc as uls_abc
from b2bapi.utils.hal import Resource as Hal

def hal():
    return Hal()._c('productlist', 'https://api.productlist.io/doc/{rel}')

# setting domain name in urls that expects it during `url_for()`
def api_url(*a, **kw):
    url = url_for(*a, **kw)
    return '/'.join([app.config['API_HOST'].strip('/'), url.lstrip('/')])

@bp.url_defaults
def set_domain(endpoint, values):
    if 'domain' in values or not getattr(g, 'domain', None):
        return
    if app.url_map.is_endpoint_expecting(endpoint, 'domain'):
        values['domain'] = g.domain.name


# removing domain name from values matched in the route and storing it in g
@bp.url_value_preprocessor
def domain_extractor(endpoint, values):
    if 'domain' not in values:
        return

    domain_name = values.pop('domain')

    try:
        domain = Domain.query.filter_by(name=domain_name).one()
    except:
        raise werk_exc.NotFound('API Not Found')
    g.domain = domain

def json_error(status_code, data=None):
    if data is None:
        data = {}
    response = jsonify(data)
    response.status_code = status_code
    corsify(response)
    return response

def json_abort(status_code, data=None):
    abort(json_error(status_code, data))

def crossorigin(fnc):
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        if request.method=='OPTIONS':
            response = app.make_default_options_response()
        else:
            response = fnc(*a, **kw)
        corsify(response)
        return response
    return wrapper

def corsify(response):

    allowed_origin_filter = re.compile(app.config['ALLOWED_ORIGINS_REGEX'])
    default_origin = app.config['SERVER_DOMAIN'].strip('/')
    request_origin = request.headers.get('origin', default_origin)

    allow_origin_match = allowed_origin_filter.match(request_origin)

    if allow_origin_match:
        allow_origin = allow_origin_match.group()
    else:
        allow_origin = default_origin

    response.headers['Access-Control-Allow-Origin'] = allow_origin

    response.headers[
        'Access-Control-Allow-Methods']='GET, POST, PUT, DELETE, PATCH, OPTIONS'
    response.headers[
        'Access-Control-Allow-Headers']=(
            'Authorization, Content-Type, Cache-Control, X-Requested-With, '
            'Location, access-token, Access-Token, Origin')
    response.headers['Access-Control-Expose-Headers'] = 'Location'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@bp.errorhandler(400) # see CATCHALL ROUTE next to this
@bp.errorhandler(401) # see CATCHALL ROUTE next to this
@bp.errorhandler(403) # see CATCHALL ROUTE next to this
@bp.errorhandler(404) # see CATCHALL ROUTE next to this
@bp.errorhandler(405) # see CATCHALL ROUTE next to this
@bp.errorhandler(409) # see CATCHALL ROUTE next to this
def errorhandler(error):
    """
    /!\ CAVEAT /!\ 
    A Blueprint.errorhandler does not catch unmapped resources based on the
    url_prefix (e.g. all resources routed to /<someprefix>/url as one might 
    initially believe. It catches errors raise from within the blueprint. That
    is, once a request has been routed to a view and over the course of that
    run an error was raised, then the Blueprint errorhandler can intervene.

    Because of this, it might be necessary to create a catchall route for the 
    Blueprint that receives all unmapped routes based on the prefix and raises
    404 so that this handler can catch it.
    """
    #response = app.response_class(
    #    json.dumps({'code': 404, 'error': 'Resource Not Found', }), 
    #    mimetype='application/json',
    #)
    #response = corsify(json_abort(404, {'code':404, 'error': 'Not Found'}))
    response = json_error(
        error.code, {'code':error.code, 'error': error.description})
    return response, error.code

@bp.route('/<path:catchall>')
def catchall(*a, **kw):
    abort(404)

def parse_keys(multidict):
    rv = MultiDict()
    for key, values in multidict.iterlists():
        keys = key.split('.')
        obj = rv
        for index, k in enumerate(keys):
            if len(keys)==index + 1:
                # last iteration
                [obj.add(k, v) for v in values]
            else:
                obj = obj.setdefault(k, MultiDict())
    return rv



def get_json_data():
    try:
        # exception will be raised if content-type is 'application/json'
        # yet there's nothing in request.json
        data = request.get_json()
    except: 
        json_abort(400, {'error': 'Data should be in JSON'})
    # if data is None, then content-type != application/json
    if data is None:
        json_abort(400, {'error': 'Data expected with Content-Type: '
                         'application/json'})
    return data

""" a bunch of params injectors for the router """
def data_injector(fnc):
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        data = get_json_data()
        return fnc(*a, data=data, **kw)
    return wrapper

def file_injector(fnc, *filenames):

    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        # OLD APPROACH: files are sent with their metadata
        # we get the file metadata, if any
        #request_charset = request.mimetype_params.get('charset')
        #try:
        #    data = request.form.get('data')
        #    if request_charset is not None:
        #        data = json.loads(data, encoding=request_charset)
        #    else:
        #        data = json.loads(data)
        #except ValueError as e:
        #    data = None
        #kw['data'] = data

        # NEW APPROACH: files sent after the metadata
        # Even though files are always expected to be sent as a bundle,
        # the route should still provide the names of the different expected
        # groups of files.
        for name in filenames:
            kw[name] = request.files.getlist(name, None)
        return fnc(*a, **kw)

    return wrapper

def params_injector(fnc):
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        params = request.args
        return fnc(*a, params=params, **kw)
    return wrapper

def lang_injector(fnc):
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        lang = g.lang
        return fnc(*a, lang=lang, **kw)
    return wrapper

def access_token_authentication():
    scheme, token = request.headers['Authorization'].split(' ')
    if scheme.lower()=='bearer':
         token
    #key = get_access_token_from_cookie()
    if not token:
        return

    try:
        secret = app.config['SECRET_KEY']
        #TODO: move the algo in the config
        payload = jwt.decode(token, secret, algorithms=['HS256'])
    except (jwt.DecodeError, jwt.ExpiredSignatureError):
        json_abort(400, {'error': 'Invalid token'})

    g.access_token = payload
    g.current_account = payload 
    return True

#def access_token_cookie_setter(fnc):
#    @functools.wraps(fnc)
#    def wrapper(*a, **kw):
#        response = fnc(*a, **kw)
#        try:
#            # a view that expects an access_token to be set must place it in g 
#            response.set_cookie(
#                token='access_token',
#                value=g.access_token,
#                httponly=True,
#                secure=app.config.get('SESSION_COOKIE_SECURE', False),
#                domain=app.config.get('SERVER_DOMAIN', None),
#            )
#        except AttributeError:
#            raise AttributeError(
#                'View function must set access_token on `flask.g`')
#        return response
#    return wrapper


#def get_csrf_token(fnc):
#    access_token_schemes = ['access-token', 'accesstoken', 'access_token']
#    try:
#        scheme, credentials = request.headers['Authorization'].split(' ')
#        if scheme.lower() in access_token_schemes:
#            return  credentials
#        return request.args['access_token']
#    except (ValueError, AttributeError, KeyError):
#        pass

#def get_access_token_from_cookie():
#    access_token_schemes = ['access-token', 'accesstoken', 'access_token']
#    try:
#        access_token = next(v for k,v in request.cookies.items() 
#                          if k in access_token_schemes)
#        return access_token
#    except StopIteration: 
#        pass

def domain_privacy_control(**kw):
    # make privacy level 'private' by default
    if g.domain.meta.get('privacy', 'private')=='public':
        return True
    try:
        return access_token_authentication()
    except (KeyError, AttributeError, ValueError): 
        return False

def authentication(fnc, processor):
    def default_processor(**kw):
        try:
            authenticated = access_token_authentication()
            #if not authenticated:
            #    authenticated = proxy_authentication()
        except (KeyError, AttributeError, ValueError) as e:
            authenticated = False
        return authenticated

    if processor is True:
        processor = default_processor

    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        authenticated = processor(**kw)
        #try:
        #    authenticated = access_token_authentication()
        #    #if not authenticated:
        #    #    authenticated = proxy_authentication()
        #except (KeyError, AttributeError, ValueError) as e:
        #    authenticated = False

        if authenticated:
            return fnc(*a, **kw)
        json_abort(
            401, {
                'error': 'Unauthenticated: invalid or missing authentication '
                'token.'})
    return wrapper

# if a resource must go through authorization an access_token should
# be present in g.
def domain_owner_authorization(**kw):
    domain_member = g.access_token.domain==g.domain.name
    return domain_member and g.access_token.role=='admin'

def account_owner_authorization(**kw):
    return g.access_token['account_id']==kw.get('account_id')

def domain_member_authorization(**kw):
    # make privacy level 'private' by default
    if g.domain.meta.get('privacy', 'private')=='public':
        return True
    member = g.access_token['domain']==g.domain.name
    return member and g.access_token.role in ['admin', 'user']

def authorization(fnc, processor):
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        dev_authorized = app.config.get('DEV_MODE', False)
        # if a resource must go through authorization an access_token should
        # be present in g.
        authorized = processor(**kw)

        if authorized or dev_authorized:
            return fnc(*a, **kw)
        json_abort(403, {'error': 'Not authorized'})
    return wrapper

def role_injector(fnc):
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        kw['role'] = g.access_token.get('role')
        return fnc(*a, **kw)
    return wrapper

def domain_injector(fnc):
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        try:
            kw['domain'] = g.domain
        except AttributeError:
            json_abort(404, {'error': 'Not Found'})
        return fnc(*a, **kw)
    return wrapper

def dbsession_rollback(fnc):
    """
    commit changes before the view.
    rolls back all changes during the view.
    """
    def wrapper(*a, **kw):
        db.session.commit()
        rv = fnc(*a,**kw)
        db.session.rollback()
        return rv
    return wrapper

def auth_injector(fnc):
    access_token_schemes = ['access_token', 'access-token', 'accesstoken']
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        try:
            scheme, credentials = request.headers['Authorization'].split()
            if scheme.lower() in access_token_schemes:
                kw['auth'] = {
                    'scheme': 'token',
                    'token': credentials,
                }
            elif scheme.lower()=='basic':
                try:
                    username, password = credentials.split(':')
                except ValueError:
                    username, password = credentials.split(':'), None
                kw['auth'] = {
                    'scheme': 'Basic',
                    'username': username,
                    'password': password,
                }

        except AttributeError:
            kw['auth'] = None
        return fnc(*a, **kw)
    return wrapper

def access_token_injector(fnc):
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        kw['access_token'] = g.access_token
        return fnc(*a, **kw)
    return wrapper 

def account_injector(fnc):
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        try:
            kw['account'] = g.current_account
        except AttributeError:
            raise AttributeError(
                '`g.current_account` not set. Ensure that the authentication '
                'processor sets it.')
        return fnc(*a, **kw)
    return wrapper

def passthrough_view(fnc, passthrough_url):
    url = passthrough_url
    # replaces view function
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        _rv = fnc(*a, **kw) or {}
        _params, _data = _rv.get('params', {}), _rv.get('data', {})
        try:
            data = request.get_json() or {}
        except:
            data = {}
        data.update(_data)
        params = MultiDict(request.args) 
        params.update(_params) if params else _params
        method = request.method
        headers = dict(request.headers)
        # /!\ make sure to always remove this when doing something like this
        headers.pop('Content-Length', None)
        resp = requests.request(
            method=method.lower(),
            url=url, json=data, params=params,
            headers=headers,
        )
        if _rv.get('callback'):
            return _rv['callback'](resp) or ('passthrough error', 500, [])
        return resp.json(), resp.status_code, []
    return wrapper

api_actions = {}

# TODO: temporary until we involve cache, then use cachelib's version
def json_response_wrapper(fnc):
    @functools.wraps(fnc)
    def wrapper(*a, **kw):
        data = fnc(*a, **kw)
        if data is None:
            raise TypeError("'NoneType' object returned from view")
        try:
            data, status, headers = data
        except ValueError as e: # (too many|need more) values to unpack 
            status, headers = 200, []
        # we'll assume that only one value was provided
        return json_response(data, status=status, headers=headers)
    return wrapper

def route(
    url_pattern, methods=None, domained=True, expects_data=False, 
    expects_params=False, expects_files=False, authenticate=False,
    authorize=None, expects_lang=False, expects_access_token=False,
    expects_role=False, expects_domain=False, expects_auth=False,
    passthrough=None, cacheable=False, if_match=False, if_none_match=False,
    endpoint=None, readonly=False, set_cookie_token=False, 
    expects_account=False, **kw):
    """ function to map  route to function """

    if methods is None: methods = ['GET',]

    def wrapper(view_func):
        fnc = view_func
        _endpoint = endpoint or fnc.__name__
        _url_pattern = url_pattern
        _domained = domained
        _methods = methods
        _authenticate = authenticate

        api_actions[_endpoint] = dict(
            fnc=fnc, 
            cacheable=cacheable,
            methods=_methods,
            domained=_domained,
            expects_account=expects_account, 
            expects_access_token=expects_access_token, 
            expects_role=expects_role, 
            expects_domain=expects_domain, 
            expects_params=expects_params,
            expects_lang=expects_lang,
            readonly=readonly,
        )


        #if cacheable:
        #    fnc = cache_wrapper(fnc, cache)

        # expects_data and expects_files are mutually exclusive 
        # having precedence

        #if passthrough:
        #    fnc = passthrough_view(fnc, passthrough)

        if readonly:
            fnc = dbsession_rollback(fnc)

        if expects_files:
            if 'basestring' not in globals():
                basestring = str
            if isinstance(expects_files, basestring): 
                filenames = [expects_files]
            else: 
                filenames = expects_files
            fnc = file_injector(fnc, *filenames)
        elif expects_data:
            fnc = data_injector(fnc)

        if expects_params:
            fnc = params_injector(fnc)

        if expects_lang:
            fnc = lang_injector(fnc)

        if expects_domain:
            # domain are extracted from the route by default, in a preprocessor 
            # defined earlier in this module. Let's reinject them:
            fnc = domain_injector(fnc)
            _domained = True

        if _domained:
            # domained is True by default, meaning that routes that do not
            # require a domain should explicitly set this to False.
            # it simply prefixes an url_pattern with the domain placeholder.

            # It is separate from a the previous option (expects_domain)
            # because even though most routes are domained, most endpoints do
            # not expect that information by default.
            # Splitting these options allows to control these requirements.
            _url_pattern = '/<domain>/' + _url_pattern.lstrip('/')

        if expects_role:
            # cannot have role without authentication
            _authenticate = _authenticate or True
            fnc = role_injector(fnc)

        if expects_access_token:
            # cannot have access_token if user not authenticated
            _authenticate = _authenticate or True
            fnc = access_token_injector(fnc)

        if expects_account:
            # cannot have access_token if user not authenticated
            if not _authenticate:
                raise Exception(
                    'The `expect_account` directive requires a user provided '
                    'authentication processor.')
            fnc = account_injector(fnc)

        if expects_auth:
            # cannot pass auth without authentication
            _authenticate = _authenticate or True
            fnc = auth_injector(fnc)

        if authorize:
            # cannot have authz without authn
            _authenticate = _authenticate or True
            fnc = authorization(fnc, processor=authorize)

        if _authenticate:
            fnc = authentication(fnc, _authenticate)


        fnc = json_response_wrapper(fnc)

        # access_token
        if set_cookie_token:
            fnc = access_token_cookie_setter(fnc)

        # crossorigin
        fnc = crossorigin(fnc)
        if 'OPTIONS' not in methods:
            methods.append('OPTIONS')

        bp.add_url_rule(_url_pattern, endpoint=_endpoint, view_func=fnc,
                               methods=_methods, **kw)

        # make sure the view_func is still usable out of the request context
        return view_func

    return wrapper
