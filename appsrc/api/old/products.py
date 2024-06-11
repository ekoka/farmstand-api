import simplejson as json
import copy
from datetime import datetime as dtm

from flask import g, current_app as app
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from ..db import db
from ..db.schema import generic as product_schema
from ..db.models.products import Product
from ..db.models.meta import ProductType, Field
from ..db.models.groups import GroupOption
from ..utils.uuid import clean_uuid
from .routes.routing import json_abort, hal, api_url
from .product_utils import patch_record, Mismatch
from .images import img_aspect_ratios
from .validation.products import (add_product, edit_product, edit_product_members)

def _update_search_index(product, lang):
    language = app.config['LOCALES'].get(lang,{}).get('language', 'simple')
    searchable = [f for f in product.fields.get('fields', []) if f.get('searchable')]
    search = []
    for f in searchable:
        value = f.get('value') or ''
        if f.get('localized'):
            try:
                value = f['value'][lang] or ''
            except (AttributeError, KeyError) as e:
                value = ''
        search.append(value)
    try:
        statement = '''
        insert into product_search (domain_id, product_id, lang, search)
        values (:domain_id, :product_id, :lang, to_tsvector(:language, :search))
        '''
        nested = db.session.begin_nested()
        db.session.execute(db.text(statement), {
            'domain_id':product.domain_id,
            'lang':lang,
            'product_id':product.product_id,
            'search': ' '.join(search),
            'language': language, })
        db.session.flush()
    except sql_exc.IntegrityError as e:
        nested.rollback()
        statement = '''
        update product_search
        set search = to_tsvector(:language, coalesce(:search))
        where product_id=:product_id and domain_id=:domain_id and lang=:lang
        '''
        try:
            db.session.execute(db.text(statement), {
                'domain_id':product.domain_id,
                'lang':lang,
                'product_id':product.product_id,
                'language': language,
                'search': ' '.join(search)})
            db.session.flush()
        except:
            db.session.rollback()
            raise

def _delocalize_product_field(field, lang):
    """
    delocalize fields, i.e. remove the lang context from field
    """
    rv = dict(**field)
    if field.get('localized'):
        try:
            rv['value'] = rv.setdefault('value', {}).get(lang)
        except AttributeError:
            pass
        rv['localized'] = True
    return rv

def _localize_product_fields(fields, lang):
    """
    localize fields, i.e. add a lang context
    """
    for field in fields:
        # if field has no value, skip
        if 'value' not in field: continue
        # if field has the `localized` flag, localize the value
        if field.get('localized'):
            field['value'] = {lang: field['value']}

def _localized_field_schema(field, lang):
    rv = {}
    rv['label'] = field['schema']['label'][lang]
    if field['field_type']=='BOOL':
        for v in (True, False):
            rv.setdefault('options',{})[v] = field['schema']['options'][v][lang]
        return rv
    if field['field_type'] in ('MULTI_CHOICE', 'SINGLE_CHOICE',):
        for o in field['schema']['options']:
            rv.setdefault('options',[]).append(
                {'value': o['value'], 'label': o['label'][lang]})
    return rv

def _field_schema(f, lang):
    field = copy.deepcopy(f['field'])
    field['display'] = f.get('display', False)
    field['searchable'] = f.get('searchable', False)
    field['localized'] = f.get('localized', False)
    field['schema'] = _localized_field_schema(field, lang)
    return field

def _recent_products(domain_id, params, lang):
    limit = 100
    #q = db.session.query(Product.product_id).filter_by(domain_id=domain_id)
    #q = q.order_by(Product.priority.asc()).order_by(Product.updated_ts.desc())
    query = '''
    select p.product_id
    from products p
    {lastproduct_subquery}
    where p.domain_id=:domain_id
    {lastproduct_filter}
    order by p.priority asc, p.updated_ts desc, p.product_id desc
    limit :limit
    '''
    qparams = dict(
        limit=limit,
        domain_id=domain_id,)
    lastproduct_filter = lastproduct_subquery = ''
    if params.get('last_product'):
        lastproduct_subquery = ''', (
        select product_id, updated_ts, priority
        from products
        where domain_id=:domain_id
            and product_id = :last_product_id
        ) lastproduct
        '''
        lastproduct_filter = ('''
        and ( p.priority > lastproduct.priority or
                (p.priority = lastproduct.priority and
                    p.updated_ts < lastproduct.updated_ts) or
                (p.priority = lastproduct.priority and
                    p.updated_ts = lastproduct.updated_ts and
                    p.product_id < lastproduct.product_id))''')
        qparams['last_product_id'] = params['last_product']
    query = query.format(
        lastproduct_subquery=lastproduct_subquery,
        lastproduct_filter=lastproduct_filter,)
    return _execute_product_query(query=db.text(query), params=qparams)

def _search_products(params, domain_id, lang):
    limit = 100
    language = app.config['LOCALES'].get(lang,{}).get('language', 'simple')
    qparams = dict(
        domain_id=domain_id,
        language=language,
        limit=limit,)
    statement = """
    select ps.product_id, ts_rank(search, query) rank
    from product_search ps,
        to_tsquery(:language, :search) query
        {lastproduct_subquery}
    where domain_id=:domain_id
        {lastproduct_filter}
        and search @@ query
    order by rank desc, product_id desc
    limit :limit
    """
    #order by ts_rank(search, to_tsquery(:language, :search)) desc, product_id desc
    lastproduct_filter = lastproduct_subquery = ''
    if params.get('last_product'):
        lastproduct_subquery = '''
        , (select product_id, ts_rank(search, to_tsquery(:language, :search)) rank
        from product_search
        where domain_id=:domain_id and product_id = :last_product_id
        ) lastproduct
        '''
        lastproduct_filter = (
            'and (lastproduct.rank, lastproduct.product_id) > (rank, ps.product_id)')
        qparams['last_product_id'] = params['last_product']
    statement = statement.format(
        lastproduct_subquery=lastproduct_subquery,
        lastproduct_filter=lastproduct_filter,)
    qparams['search'] = '|'.join(
        s.strip() for s in params['q'].split(' ') if s.strip())
    return _execute_product_query(query=db.text(statement), params=qparams)

def _execute_product_query(query, params):
    # fetch one more item just to test if we've reached end of list
    limit = params['limit'] + 1 if params.get('limit') else None
    rows = db.session.execute(query, params).fetchall()
    has_more = False
    if limit and len(rows) > limit:
        # if it's possible to fetch the extra item
        # it implies that there may be more rows.
        has_more = True
        rows.pop(-1)
    return {
        'product_ids':  [clean_uuid(r.product_id) for r in rows],
        'last_product': rows[-1].product_id if rows else None,
        'has_more': has_more, }


def get_products(params, domain, lang):
    _get_products = _search_products if params.get('q') else _recent_products
    result = _get_products(params=params, domain_id=domain.domain_id, lang=lang)
    product_url = api_url('api.get_product', product_id='{product_id}')
    rv = hal()
    rv._l('self', api_url('api.get_products', **params))
    rv._l(f'{app.config.API_NAMESPACE}:product', product_url, unquote=True, templated=True)
    rv._k('product_ids', result['product_ids'])
    rv._k('last_product', result['last_product'])
    rv._k('has_more', result['has_more'])
    return rv.document, 200, []


def get_product_resources(params, domain, lang):
    product_ids = params.getlist('pid')
    q = Product.query.filter_by(domain_id=domain.domain_id)
    if product_ids:
        q = q.filter(Product.product_id.in_(product_ids))
    products = q.all()
    rv = hal()
    rv._l('self', api_url('api.get_product_resources'))
    rv._k('product_ids', [p.product_id for p in products])
    rv._embed('products', [_get_product_resource(p, lang) for p in products])
    return rv.document, 200, []


def get_product_schema(lang):
    rv = hal()
    rv._l('self', api_url('api.get_product_schema'))
    rv._k('name', product_schema['name'])
    rv._k('fields', [_field_schema(f, lang) for f in product_schema['schema']['fields']])
    return rv.document, 200, []


def get_product_json(product_id, domain):
    product = _get_product(product_id, domain.domain_id)
    data = json.dumps(product.fields, indent=4)
    return {'json':data}, 200, []


def put_product_json(product_id, domain, data):
    product = _get_product(product_id, domain.domain_id)
    product.fields = data
    db.session.flush()
    return {}, 200, []

def _get_product(product_id, domain_id):
    product_id = clean_uuid(product_id)
    try:
        if product_id is None:
            raise orm_exc.NoResultFound()
        return Product.query.filter_by(product_id=product_id, domain_id=domain_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error': 'Product Not Found'})

def get_product(product_id, domain, params, lang):
    # in the meantime, while waiting for validation
    partial = int(params.get('partial', False))
    product = _get_product(product_id, domain.domain_id)
    document = _get_product_resource(product, lang)
    return document, 200, []

def _get_product_resource(p, lang):
    rv = hal()
    rv._l('self', api_url(
        'api.get_product', product_id=clean_uuid(p.product_id)))
    rv._l('images', api_url(
        'api.get_product_images', product_id=clean_uuid(p.product_id)))
    rv._l('groups', api_url(
        'api.put_product_groups', product_id=clean_uuid(p.product_id)))
    rv._k('product_id', clean_uuid(p.product_id))
    rv._k('groups', _get_product_groups(p))
    rv._k('priority', p.priority)
    rv._k('last_update', p.updated_ts)
    rv._k('images', [img_aspect_ratios(
        i.image, aspect_ratios=['1:1'], sizes=['thumb', 'medium'])
        for i in p.images ])
    rv._k('fields', [_delocalize_product_field(f, lang)
                     for f in p.fields.setdefault('fields', [])])
    # NOTE: maybe we'll add this at some point
    #rv._k('unit_price', p.data.get('unit_price'))
    #rv._k('quantity_unit', p.data.get('quantity_unit'))
    # TODO:
    #rv._embed('groups', [_get_group_resource(f, True) for f in p.groups])
    return rv.document

def _get_product_groups(p):
    rv = {}
    for fo in p.group_options:
        rv.setdefault(clean_uuid(fo.group_id), []).append(
            clean_uuid(fo.group_option_id))
    return rv

def populate_product(product, data, lang):

    for k,v in data.items():
        if k=='fields':
            # NOTE: disabling merging with localization
            # _merge_fields(product.fields, v, lang)
            product.fields['fields'] = v
            continue
        setattr(product, k, v)

def _merge_fields(productfields, fields, lang):
    # productfields: database fields to update
    # fields: fresh data to populate the fields
    # loop through the uploaded fields
    for f in fields:
        # if field is not a text type, skip
        if not f.get('localized'): continue
        # extract the uploaded value and reset the field value
        # to an empty dict, ready to take localized values
        f['value'], value = {}, f.get('value')
        # now we search if the product already has an existing
        # field with the same name.
        for pf in productfields['fields']:
            if pf.get('name')!=f['name']: continue
            # if we find a matching field we give its (localized)
            # value to our just uploaded field's value
            if isinstance(pf['value'], dict):
                f['value'] = pf['value']
                continue
            # if field was not localized before and now is
            # TODO: pick default lang from config
            default_lang = 'en'
            f['value'] = {default_lang: pf['value']}
        # now whether the field was already present or not
        # we set the uploaded value as a localized value
        f['value'][lang] = value
    # we're now ready to replace the old fields with the new data set
    productfields['fields'] = fields

def db_flush():
    try:
        db.session.flush()
    except sql_exc.IntegrityError as e:
        db.session.rollback()
        app.logger.info('problem saving in the database')
        json_abort(400, {'error': 'Problem while saving data'})

def post_product(data, lang):
    try:
        data = add_product.validate(data)
    except vno_err.ValidationErrorStack as e:
        json_abort(400, {'error': 'Invalid data ' + str(e)})
    p = Product(fields={'fields': []}) # enveloped
    #record(**data)
    populate_product(p, data, lang)
    db.session.add(p)
    db_flush()
    location = api_url(
        'api.get_product', product_id=p.product_id, partial=False)
    rv = hal()
    rv._l('location', location)
    rv._k('product_id', p.product_id)
    return rv.document, 201, [('Location', location)]

def put_product(product_id, data, domain, lang):
    data = edit_product.validate(data)
    p = _get_product(product_id, domain.domain_id)
    p.updated_ts = dtm.utcnow()
    populate_product(p, data, lang)
    db_flush()
    _update_search_index(p, lang)
    return {}, 200, []

def put_product_groups(product_id, data, domain):
    #TODO: validation
    groups = data.get('groups') or  []
    try:
        update_group_options(product_id, groups, domain.domain_id)
    except:
        db.session.rollback()
        # TODO: turn this on only when DEBUG
        raise
        json_abort(400, {'error':'Bad format'})
    return {}, 200, []

def get_product_details(domain, lang, params):
    #TODO: validate params
    product_ids = params.getlist('pid')
    rv = hal()
    rv._l('self', api_url('api.get_product_details'))
    products = Product.query.filter(
        Product.product_id.in_(product_ids),
        Product.domain_id==domain.domain_id,).all()
    rv._embed('products', [_get_product_resource(p, lang) for p in products])
    return rv.document, 200, []

def update_group_options(product_id, groups, domain_id):
    try:
        db.session.execute(db.text(
            'DELETE FROM products_group_options WHERE domain_id=:domain_id '
            'AND product_id=:product_id'), {
                'domain_id':domain_id, 'product_id':product_id, })
    except:
        db.session.rollback()
        raise
        json_abort(400, {'error': 'Bad format'})
    if not groups:
        return
    options = []
    for group_id,group_options in groups.items():
        options.extend(GroupOption.query.filter(
            GroupOption.group_id==group_id,
            GroupOption.group_option_id.in_(group_options),
            GroupOption.domain_id==domain_id,
        ).all())
    new = [{
        'domain_id': domain_id,
        'product_id': product_id,
        'group_option_id': o.group_option_id, } for o in options]
    if new:
        db.session.execute(db.text(
            'insert into products_group_options '
            '(domain_id, group_option_id, product_id) values '
            '(:domain_id, :group_option_id, :product_id)'), new)
    try:
        db.session.flush()
    except:
        db.session.rollback()
        raise

"""
For a data to be patched to the product, it must already be present.
"""
def patch_product(product_id, data, domain, lang):
    #TODO: validation
    #data = edit_product_members.validate(data)
    p = _get_product(product_id, domain.domain_id)
    try:
        _localize_product_fields(data['fields'], lang)
    except (ValueError, AttributeError, TypeError):
        raise
        json_abort(400, {'error': 'Bad format'})
    try:
        patch_record(p, data)
    except Mismatch:
        db.session.rollback()
        json_abort(400, {'error': 'Badly formed data'})
    db_flush()
    return {}, 200, []

def delete_product(product_id):
    try:
        p = _get_product(product_id)
        db.session.delete(p)
        db.session.flush()
        #.products.delete().where(
        #    (products.c.domain_id==g.domain['domain_id'])&
        #    (products.c.product_id==product_id)))
    except:
        pass
    return ({}, 200, [])

def grouped_query(q, groups):
    group_path = 'data#>\'{{fields,{name},value}}\''
    text_group = '{} @> \'"{{value}}"\''.format(group_path)
    bool_group = '{} @> \'{{value}}\''.format(group_path)
    for n,v in groups:
        formatter = text_group.format
        if v in (True,False):
            v = str(v).lower()
            formatter = bool_group.format
        q = q.filter(db.text(formatter(name=n, value=v)))
    return q
