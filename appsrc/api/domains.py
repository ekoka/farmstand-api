from .routes.routing import api_url, hal
from .utils import delocalize_data, run_or_abort
from ..db.models.domains import Domain
from ..utils.uuid import clean_uuid
from ..service import domains as domain_srv

# the expects_access_token directive also implies authenticate
def post_domain(data, access_token, lang):
    # api
    #TODO: Validation
    fnc = lambda: domain_srv.create_domain(data, access_token, lang)
    domain = run_or_abort(fnc)
    rv = hal()
    domain_url = api_url('api.get_domain', domain_name=domain.name)
    rv._l('location', domain_url)
    rv._k('domain_name', domain.name)
    return rv.document, 201, [('Location', domain_url)]

def _subscription_data(subscription):
    # api - data template
    #TODO
    #"current_period_start": 1552054799,
    #"current_period_end": 1554733199,
    #"status": "active",
    return {
        "id": "sub_Ef3fWeFTQIbqr5",
        "billing_cycle_anchor": 1552054799,
        "canceled_at": null,
        "created": 1552054799,
        "quantity": 1,
        "start": 1552054799,
        "tax_percent": null,
        "trial_start": null,
        "trial_end": null,
        "default_source": null,
        "discount": null,
        "ended_at": null,
        "latest_invoice": null,
        "metadata": {},
        "plan": {
            "id": "gold",
            "amount": 2000,
            "currency": "cad",
            "interval": "month",
            "interval_count": 1,
            "nickname": null,
            "product": "prod_BTMywD3UV6AkeY",
            "trial_period_days": null, }, }

# We only need to authenticate since the domain list is matched against the
# authenticated account anyways
def get_domains(access_token, lang):
    # api
    fnc = lambda: domain_srv.get_domains(access_token, lang)
    (account, roles) = run_or_abort(fnc)
    domains = [_get_domain_resource(account_domain.domain, lang)
               for account_domain in account.domains]
    rv = hal()
    rv._l('self', api_url('api.get_domains'))
    rv._embed('domains', domains)
    rv._k('roles', roles)
    return rv.document, 200, []

def _get_domain_resource(domain, lang):
    # api - resource
    domain_url = api_url('api.get_domain', domain_name=domain.name)
    product_schema_url = api_url('api.get_product_schema', domain=domain.name)
    groups_url = api_url('api.get_groups', domain=domain.name)
    group_url = api_url('api.get_group', domain=domain.name,
                          group_id='{group_id}')
    accounts_url = api_url('api.get_domain_accounts', domain=domain.name)
    account_url = api_url('api.get_domain_account', domain=domain.name,
                          account_id='{account_id}')
    access_requests_url = api_url('api.get_domain_access_requests',
                                  domain=domain.name)
    group_resources_url = api_url(
        'api.get_group_resources', domain=domain.name)
    products_url = api_url('api.get_products', domain=domain.name)
    product_url = api_url('api.get_product', domain=domain.name,
                          product_id='{product_id}')
    product_json_url = api_url('api.get_product_json', domain=domain.name,
                               product_id='{product_id}')
    product_details_url = api_url('api.get_product_details', domain=domain.name)
    product_resources_url = api_url(
        'api.get_product_resources', domain=domain.name)
    source_images_url = api_url('api.post_source_image', domain=domain.name)
    images_url = api_url('api.get_images', domain=domain.name)
    #inquiries_url = api_url('api.get_inquiries', domain=domain.name)
    rv = hal()._l('self', domain_url)
    rv._k('name', domain.name)
    rv._k('creation_date', domain.creation_date.date())
    rv._l(f'{app.config.API_NAMESPACE}:product_schema', product_schema_url)
    rv._l(f'{app.config.API_NAMESPACE}:groups', groups_url)
    rv._l(f'{app.config.API_NAMESPACE}:domain_accounts', accounts_url)
    rv._l(f'{app.config.API_NAMESPACE}:domain_account', account_url, unquote=True,
          templated=True)
    rv._l(f'{app.config.API_NAMESPACE}:domain_access_requests', access_requests_url)
    rv._l(f'{app.config.API_NAMESPACE}:group_resources', group_resources_url)
    rv._l(f'{app.config.API_NAMESPACE}:group', group_url, unquote=True, templated=True)
    rv._l(f'{app.config.API_NAMESPACE}:products', products_url)
    rv._l(f'{app.config.API_NAMESPACE}:source_images', source_images_url)
    rv._l(f'{app.config.API_NAMESPACE}:images', images_url)
    #rv._l(f'{app.config.API_NAMESPACE}:inquiries', inquiries_url)
    rv._l(f'{app.config.API_NAMESPACE}:product', product_url, unquote=True, templated=True)
    rv._l(f'{app.config.API_NAMESPACE}:product_json', product_json_url, unquote=True,
          templated=True)
    rv._l(f'{app.config.API_NAMESPACE}:product_details', product_details_url)
    rv._l(f'{app.config.API_NAMESPACE}:product_resources', product_resources_url)
    # include company info
    rv._k('data', delocalize_data(domain.data, Domain.localized_fields, lang))
    rv._k('meta', domain.meta)
    return rv.document

def get_domain(domain_name, lang):
    # api
    fnc = lambda: domain_srv.get_domain(domain_name)
    domain = run_or_abort(fnc)
    return _get_domain_resource(domain, lang), 200, []

def put_domain(domain_name, data, lang):
    # api
    # TODO: validation
    fnc = lambda: domain_srv.update_domain(domain_name, data, lang)
    run_or_abort(fnc)
    return {}, 200, []

def get_domain_name_check(params):
    # api
    name = params.get('q')
    try:
        domain_srv.check_domain_name(name)
        return {}, 200, []
    except srv_err.ServiceError as e:
        return {}, e.code, []

def post_domain_account(data, domain):
    # api
    # TODO validation
    # TODO: add a routine for user to approve the domain they're being added to
    fnc = lambda: domain_srv.create_domain_account(data, domain)
    run_or_abort(fnc)
    return {}, 200, []

def delete_domain_account(account_id, domain):
    # api
    fnc = lambda: domain_srv.delete_domain_account(account_id, domain)
    run_or_abort(fnc)
    return {}, 200, []

def get_domain_accounts(domain, params):
    # api
    fnc = lambda: domain_srv.get_domain_accounts(domain, params.get('active'))
    accounts = run_or_abort(fnc)
    rv = hal()
    rv._l('self', api_url('api.get_domain_accounts'))
    rv._embed('accounts', [_get_domain_account_resource(a) for a in accounts])
    return rv.document, 200, []

def get_domain_account(domain, account_id):
    # api
    fnc = lambda: domain_srv.get_domain_account(
        domain_id=domain.domain_id, account_id=account_id)
    account = run_or_abort(fnc)
    rv = get_domain_account_resource(account)
    return rv, 200, []

def get_domain_account_resource(domain_account):
    # api - resource
    account = domain_account.account
    resource = hal()
    resource._l('self', api_url(
        'api.get_domain_account', account_id=account.account_id))
    resource._k('account_id', domain_account.account_id)
    resource._k('name', account.name)
    resource._k('email', account.email)
    resource._k('role', domain_account.role)
    resource._k('active', domain_account.active)
    return resource.document

def post_access_request(account, data):
    # api
    # TODO validation
    fnc = lambda: domain_srv.create_access_request(account, data)
    domain = run_or_abort(fnc)
    rv = hal()
    location = api_url('api.get_access_request', domain_id=domain.domain_id)
    rv._l('location', location)
    return rv.document, 201, [('Location', location)]

def get_access_request(domain_id, account):
    # api
    fnc = lambda: domain_srv.get_access_request_by_account(domain_id, account)
    access_request = run_or_abort(fnc)
    rv = hal()
    rv._l('self', api_url('api.get_access_request', domain_id=domain_id))
    rv._k('status', access_request.status)
    rv._k('data', access_request.data)
    rv._k('created', access_request.creation_date)
    return rv.document, 200, []

def get_domain_access_requests(domain, lang):
    # api
    fnc = lambda: domain_srv.get_domain_access_requests(domain, lang)
    access_requests = run_or_abort(fnc)
    access_request_resources = [_get_domain_access_request_resources(record, lang)
                                for record in access_requests]
    rv = hal()
    rv._l('self', api_url('api.get_domain_access_requests'))
    rv._l('domain', api_url('api.get_domain', domain_name=domain.name))
    rv._embed('access_requests', access_request_resources)
    return rv.document, 200, []

def get_domain_access_request(access_request_id, lang):
    # api
    fnc = lambda: domain_srv.get_access_request_by_id(access_request_id)
    access_request = run_or_abort(fnc)
    document = _get_domain_access_request_resources(access_request, lang)
    return document, 200, []

def _get_domain_access_request_resources(access_request, lang):
    # api - resource
    rv = hal()
    rv._l('self', api_url(
        'api.get_domain_access_request', access_request_id=clean_uuid(
            access_request.access_request_id)))
    rv._k('access_request_id', clean_uuid(access_request.access_request_id))
    rv._k('status', access_request.status)
    rv._k('creation_date', access_request.creation_date)
    rv._k('message', access_request.data.get('message'))
    account = access_request.account
    account_data = delocalize_data(account.data, account.localized_fields, lang)
    account_resource = {
        "account_id": account.account_id,
        "name": account.name,
        "email": account.primary_email and account.primary_email.email, }
    account_resource.update({
        f: account_data.get(f) for f in access_request.data.get('fields', [])
    })
    rv._k('account', account_resource)
    return rv.document

def patch_domain_access_request(access_request_id, data):
    # api
    # TODO: validation
    fnc = lambda: domain_srv.update_access_request_status(
            access_request_id, data.get('status'))
    run_or_abort(fnc)
    return {}, 200, []
