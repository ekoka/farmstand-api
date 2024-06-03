import copy
from datetime import datetime as dtm

from flask import current_app as app
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from ..db import db
from ..db.models.products import Product
from ..db.models.groups import GroupOption
from ..utils.uuid import clean_uuid
from .product_utils import patch_record, Mismatch
from .validation.products import (add_product, edit_product, edit_product_members)

def update_search_index(product, lang):
    # service
    language = app.config['LOCALES'].get(lang,{}).get('language', 'simple')
    searchable = (f for f in product.fields.get('fields', []) if f.get('searchable'))
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
            raise err.ServiceError('Could not update data for product search')

def localized_product_fields(fields, lang):
    # service
    """
    Build and return localized version of fields, i.e. add a lang context.
    """
    rv = []
    for f in fields:
        new_f = copy.deepcopy(f)
        if new_f.get('localized'):
            # If field has the `localized` flag, localize its value.
            localized_value = {lang: new_f.get('value')}
            new_f['value'] = localized_value
        rv.append(new_f)
    return rv

def recent_products(domain_id, lang, last_product_id=None):
    # service
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
    if last_product_id:
        qparams['last_product_id'] = last_product_id
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
    query = query.format(
        lastproduct_subquery=lastproduct_subquery,
        lastproduct_filter=lastproduct_filter,)
    return _execute_product_query(query=db.text(query), params=qparams)

def search_products(domain_id, lang, last_product_id=None, search_query=''):
    # service
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
    if last_product_id:
        lastproduct_subquery = '''
        , (select product_id, ts_rank(search, to_tsquery(:language, :search)) rank
        from product_search
        where domain_id=:domain_id and product_id = :last_product_id
        ) lastproduct
        '''
        lastproduct_filter = (
            'and (lastproduct.rank, lastproduct.product_id) > (rank, ps.product_id)')
        qparams['last_product_id'] = last_product_id
    statement = statement.format(
        lastproduct_subquery=lastproduct_subquery,
        lastproduct_filter=lastproduct_filter,)
    qparams['search'] = '|'.join(
        s.strip() for s in search_query.split(' ') if s.strip())
    return execute_product_query(query=db.text(statement), params=qparams)

def execute_product_query(query, params):
    # service
    # Fetch one more item just to test if we've reached end of list.
    limit = params['limit'] + 1 if params.get('limit') else None
    rows = db.session.execute(query, params).fetchall()
    has_more = False
    if limit and len(rows) > limit:
        # If it's possible to fetch the extra item,
        # it means that there may be more rows.
        has_more = True
        rows.pop(-1)
    return {
        'product_ids':  [clean_uuid(r.product_id) for r in rows],
        'last_product': rows[-1].product_id if rows else None,
        'has_more': has_more, }

def get_products(domain, lang, last_product_id, search_query=None):
    # service
    args = (search_query,) if search_query else ()
    _get_products = search_products if search_query else recent_products
    return _get_products(domain, lang, last_product_id, *args)

def get_product_by_ids(product_ids, domain_id, lang):
    # service
    q = Product.query.filter_by(domain_id=domain_id)
    if product_ids:
        q = q.filter(Product.product_id.in_(product_ids))
    products = q.all()

def set_product_fields(product_id, domain_id, data):
    # service
    product = get_product(product_id, domain_id)
    product.fields = data
    db.session.flush()
    return product

def get_product(product_id, domain_id):
    # service
    notfound = lambda: err.NotFound('Product not found')
    product_id = clean_uuid(product_id)
    if not product_id:
        raise notfound()
    try:
        return Product.query.filter_by(product_id=product_id, domain_id=domain_id).one()
    except orm_exc.NoResultFound as e:
        raise notfound()

def get_product_groups(p):
    # service
    rv = {}
    add_option = lambda opt: rv.setdefault(
        clean_uuid(opt.group_id), []).append(clean_uuid(opt.group_option_id))
    for g_o in p.group_options:
        add_option(g_o)
    return rv

def populate_product(product, data, lang):
    # service
    for k,v in data.items():
        if k=='fields':
            # NOTE: disabling merging with localization
            # _merge_fields(product.fields, v, lang)
            product.fields['fields'] = v
            continue
        setattr(product, k, v)

def _merge_fields(productfields, fields, lang):
    # service
    # productfields: database fields to update
    # fields: fresh data to populate the fields
    # Loop through the uploaded fields.
    for f in fields:
        # If field is not a text type, skip.
        if not f.get('localized'): continue
        # Extract the uploaded value and reset the field value
        # to an empty dict, ready to take localized values.
        f['value'], value = {}, f.get('value')
        # Now, we search if the product already has an existing
        # field with the same name.
        for pf in productfields['fields']:
            if pf.get('name')!=f['name']: continue
            # If we find a matching field we give its (localized)
            # value to our just uploaded field's value.
            if isinstance(pf['value'], dict):
                f['value'] = pf['value']
                continue
            # If field was not localized before and now is.
            # TODO: Pick default lang from config.
            default_lang = 'en'
            f['value'] = {default_lang: pf['value']}
        # Now, whether the field was already present or not,
        # we set the uploaded value as a localized value.
        f['value'][lang] = value
    # We're now ready to replace the old fields with the new data set.
    productfields['fields'] = fields

def db_flush():
    # service
    try:
        db.session.flush()
    except sql_exc.IntegrityError as e:
        db.session.rollback()
        raise err.FormatError('Problem while saving data')

def create_product(data, lang):
    # service
    try:
        data = add_product.validate(data)
    except vno_err.ValidationErrorStack as e:
        raise err.FormatError(f'Invalid data: {str(e)}')
    p = Product(fields={'fields': []}) # envelop
    populate_product(p, data, lang)
    db.session.add(p)
    db_flush()
    return p

def update_product(product_id, data, domain_id, lang):
    # service
    data = edit_product.validate(data)
    p = prod_srv.get_product(product_id, domain_id)
    p.updated_ts = dtm.utcnow()
    populate_product(p, data, lang)
    db_flush()
    return p

def update_product_groups(product_id, groups, domain_id):
    # service
    #TODO: validation
    try:
        update_group_options(product_id, groups, domain_id)
    except:
        db.session.rollback()
        raise err.FormatError('Could not update product groups')

def product_details(domain, params):
    # service
    product_ids = params.getlist('pid')
    products = Product.query.filter(
        Product.product_id.in_(product_ids),
        Product.domain_id==domain.domain_id,).all()
    return products

def update_group_options(product_id, groups, domain_id):
    # service
    try:
        db.session.execute(db.text(
            'DELETE FROM products_group_options WHERE domain_id=:domain_id '
            'AND product_id=:product_id'), {
                'domain_id':domain_id, 'product_id':product_id, })
    except:
        db.session.rollback()
        raise err.FormatError('Could not delete products group options')
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
        raise err.FormatError('Could not update products group options')

def patch_product(product_id, domain_id, data, lang):
    # service
    #TODO: validation
    #data = edit_product_members.validate(data)
    p = get_product(product_id, domain_id)
    try:
        data['fields'] = localized_product_fields(data['fields'], lang)
    except (ValueError, AttributeError, TypeError):
        raise err.FormatError('Could not patch product fields')
    try:
        patch_record(p, data)
    except Mismatch:
        db.session.rollback()
        raise err.FormatError('Could not patch product data')
    db_flush()
    return p

def delete_product(product_id):
    # service
    try:
        p = prod_srv.get_product(product_id)
        db.session.delete(p)
        db.session.flush()
        #.products.delete().where(
        #    (products.c.domain_id==g.domain['domain_id'])&
        #    (products.c.product_id==product_id)))
    except: pass

def grouped_query(q, groups):
    # service
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
