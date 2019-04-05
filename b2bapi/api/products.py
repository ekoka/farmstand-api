import uuid
import simplejson as json
import copy
from datetime import datetime as dtm

from flask import redirect, g, current_app as app, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db import db
from b2bapi.db.models.products import Product
from b2bapi.db.models.meta import ProductType, Field
from b2bapi.db.models.groups import GroupOption
from b2bapi.utils.uuid import clean_uuid
from b2bapi.db.schema import generic as product_schema
from ._route import route, json_abort, hal
from .product_utils import patch_record, Mismatch

def _delocalize_product_field(field, lang):
    rv = dict(**field)
    if field.get('localized'):
        rv['value'] = rv.setdefault('value', {}).get(lang)
    return rv

def _localize_product_fields(fields, lang):
    for field in fields:
        if 'value' not in field:
            continue
        if field.get('localized'):
            field['value'] = {lang: field['value']}

from .images import img_aspect_ratios

from .validation.products import (add_product, edit_product, edit_product_members)

def _products_query(domain_id, **params):
    q = db.session.query(Product.product_id).filter_by(domain_id=domain_id)
    q = q.order_by(Product.priority.asc()).order_by(Product.updated_ts.desc())
    return q

@route('/products', expects_params=True, expects_domain=True,
       authenticate=True, expects_lang=True, readonly=True)
def get_products(params, domain, lang):
    products = _products_query(domain_id=domain.domain_id).all()
    product_url = url_for('api.get_product', product_id='{product_id}')
    rv = hal()
    rv._l('self', url_for('api.get_products', **params))
    rv._l('productlist:product', product_url, unquote=True, templated=True)
    rv._k('product_ids', [p.product_id for p in products])
    return rv.document, 200, []

@route('/product-resources', expects_params=True, expects_lang=True,
       expects_domain=True, authenticate=True, readonly=True)
def get_product_resources(params, domain, lang):
    product_ids = params.getlist('pid')
    q = Product.query.filter_by(domain_id=domain.domain_id)

    if product_ids:
        q = q.filter(Product.product_id.in_(product_ids))
    products = q.all()

    rv = hal()
    rv._l('self', url_for('api.get_product_resources'))
    rv._k('product_ids', [p.product_id for p in products])
    rv._embed('products', [_get_product_resource(p, lang) for p in products])
    return rv.document, 200, []


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
    field['schema'] = _localized_field_schema(field, lang)
    return field

# NOTE: just an alias route
@route('/product-template', endpoint='get_product_template', expects_lang=True)
@route('/product-schema', expects_lang=True) 
def get_product_schema(lang):
    rv = hal()
    rv._l('self', url_for('api.get_product_schema'))
    rv._k('name', product_schema['name'])
    rv._k('fields', [_field_schema(f, lang) 
                     for f in product_schema['schema']['fields']])
    return rv.document, 200, []

@route('/products/<product_id>/json', authenticate=True, expects_domain=True)
def get_product_json(product_id, domain):
    product = _get_product(product_id, domain.domain_id)
    data = json.dumps(product.fields, indent=4)
    return {'json':data}, 200, []

@route('/products/<product_id>/json', methods=['put'], authenticate=True,
       expects_domain=True, expects_data=True)
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
        return Product.query.filter_by(product_id=product_id, 
                                       domain_id=domain_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error': 'Product Not Found'})

@route('/products/<product_id>', authenticate=True, expects_domain=True,
       expects_params=True, expects_lang=True)
def get_product(product_id, domain, params, lang):
    # in the meantime, while waiting for validation
    partial = int(params.get('partial', False))
    product = _get_product(product_id, domain.domain_id)
    document = _get_product_resource(product, lang)
    return document, 200, []

def _get_product_resource(p, lang):
    rv = hal()
    rv._l('self', url_for(
        'api.get_product', product_id=clean_uuid(p.product_id)))
    rv._l('images', url_for(
        'api.get_product_images', product_id=clean_uuid(p.product_id)))
    rv._l('groups', url_for(
        'api.put_product_groups', product_id=clean_uuid(p.product_id)))

    rv._k('product_id', clean_uuid(p.product_id))

    rv._k('groups', _get_product_groups(p))
    rv._k('priority', p.priority)
    rv._k('last_update', p.updated_ts)

    rv._k('images', [img_aspect_ratios(
        i.image, aspect_ratios=['1:1'], sizes=['thumb', 'medium'])
        for i in p.images
    ])

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
        rv.setdefault(clean_uuid(fo.group_id), []).append(clean_uuid(
            fo.group_option_id))
    return rv


def load_field_metas(schema_names, domain_id):
    # query the db for fields with those names and produce
    # a dict indexed by those names
    fields = Field.query.filter(Field.domain_id==domain_id, 
                                Field.name.in_(schema_names)).all()
    return {f.name:f for f in fields}


def populate_product(product, data, lang):
    for k,v in data.items():
        if k=='fields':
            _merge_fields(product.fields, v, lang)
        else:
            setattr(product,k,v)


def _merge_fields(productfields, fields, lang):
    # loop through the uploaded fields
    for f in fields:
        # if field is a text type
        if f.get('localized'):
            # extract the uploaded value and reset the field value
            # to an empty dict, ready to take localized values
            f['value'], value = {}, f.get('value')

            # now we search if the product already has an existing field with
            # the same name
            for pf in productfields['fields']:
                # if we find a matching field we give its (localized) value
                # to our just uploaded field's value
                if pf.get('name')==f['name']:
                    f['value'] = pf.get('value', {})
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

@route('/products', methods=['POST'], expects_data=True, expects_lang=True)
def post_product(data, lang):
    try:
        data = add_product.validate(data)
    except vno_err.ValidationErrorStack as e:
        json_abort(400, {'error': 'Invalid data ' + str(e)})
    p = Product(fields={'fields': []})
    #record(**data)
    populate_product(p, data, lang)
    db.session.add(p)
    db_flush()
    location = url_for('api.get_product', product_id=p.product_id, partial=False)
    rv = hal()
    rv._l('location', location)
    rv._k('product_id', p.product_id)

    return rv.document, 201, [('Location', location)]


@route('/products/<product_id>', methods=['PUT'], expects_data=True,
       authenticate=True, expects_domain=True, expects_lang=True)
def put_product(product_id, data, domain, lang):
    data = edit_product.validate(data)
    p = _get_product(product_id, domain.domain_id)
    p.updated_ts = dtm.utcnow()
    populate_product(p, data, lang)
    db_flush()
    return {}, 200, []

@route('/products/<product_id>/groups',
       methods=['PUT'], expects_domain=True, expects_data=True,
       authenticate=True)
def put_product_groups(product_id, data, domain):
    #TODO: validation
    groups = data.get('groups') or  []
    try:
        update_group_options(product_id, groups, domain.domain_id)
    except:
        db.session.rollback()
        raise
        json_abort(400, {'error':'Bad format'})
    return {}, 200, []

@route('/products/details', expects_params=True, expects_domain=True,
       authenticate=True, expects_lang=True)
def get_product_details(domain, lang, params):
    #TODO: validate params
    product_ids = params.getlist('pid')
    rv = hal()
    rv._l('self', url_for('api.get_product_details'))
    products = Product.query.filter(
        Product.product_id.in_(product_ids),
        Product.domain_id==domain.domain_id,
    ).all()
    rv._embed('products', [_get_product_resource(p, lang)
                           for p in products])
    return rv.document, 200, []

def update_group_options(product_id, groups, domain_id):
    try:
        db.session.execute(
            'DELETE FROM products_group_options WHERE domain_id=:domain_id ' 
            'AND product_id=:product_id',
            {
                'domain_id':domain_id, 
                'product_id':product_id,
            })
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
        'group_option_id': o.group_option_id, 
    } for o in options]

    if new:
        db.session.execute(
            'insert into products_group_options '
            '(domain_id, group_option_id, product_id) values '
            '(:domain_id, :group_option_id, :product_id)', new)

    try:
        db.session.flush()
    except:
        raise
        db.session.rollback()

"""
For a data to be patched to the product, it must already be present. 
"""
@route('/products/<product_id>', methods=['PATCH'], expects_data=True,
       expects_domain=True, expects_lang=True, authenticate=True)
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

@route('/products/<product_id>', methods=['DELETE'])
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
        if v in (True,False):
            v = str(v).lower()
            q = q.filter(db.text(bool_group.format(name=n, value=v)))
        else:
            q = q.filter(db.text(text_group.format(name=n, value=v)))
    return q


#@route('/products', methods=['GET'], expects_params=True, expects_lang=True)
#def get_products(params, lang):
#    max_id = None
#    min_id = None
#    domain_id = g.domain['domain_id']
#    q = Product.query.filter_by(domain_id=domain_id)
#    if params.get('groups'): 
#        groups = json.loads(params['groups'])
#        q = grouped_query(q, [(k,v) for k,v in groups.iteritems()])
#    #_p_order = lambda p: p.data['fields_order'][0]
#    products = q.all()
#    rv = {
#        'self': url_for('api.get_products',**params),
#        'products': [_product_summary(p, lang) for p in products],
#    }
#    return rv, 200, []

#def _product_summary(p, lang):
#    return {
#        'self': url_for('api.get_product_summary', product_id=p.product_id),
#        'product_id': p.product_id.hex,
#        #'caption': _caption(p.data, lang),
#        'captionable_fields': _caption_fields(p.data['fields'], lang),
#        'url': url_for('api.get_product', product_id=p.product_id),
#    } 

#def _caption_fields(fields, lang):
#    rv = []
#    for f in fields:
#        if f.get('field_type')=='SHORT_TEXT' and f.get('value', {}).get(lang):
#            rv.append({'value': f['value'][lang], 'captionable': f.get('captionable')})
#    return rv

#def _caption(data, lang):
#    ''' caption is made of either:
#        1- all the fields that have the `captionable` flag
#        2- the field with the `caption` name
#        3- the first SHORT_TEXT field
#    '''
#    rv = ''
#    try:
#        captionable = []
#        named_caption = None
#        short_text_caption = None
#        for f in data['fields']:
#            # only SHORT_TEXT can be part of caption
#            if f['field_type']!='SHORT_TEXT':
#                continue
#            if not short_text_caption:
#                short_text_caption = f['value'][lang]
#            if not named_caption and f.get('name')=='caption':
#                named_caption = f['value'][lang]
#            if f.get('captionable') and f['value'][lang]:
#                captionable.append(f['value'][lang])
#        # TODO: put the separator in a config
#        caption = '-'.join(captionable) or named_caption or short_text_caption
#        return caption or ''
#    except:
#        return ''




# TODO: temporarily hardwired 
#@route('/product-templates/<product_type_id>', methods=['GET'])
#def get_product_template(product_type_id):
#    domain_id = g.domain['domain_id']
#    product_type = ProductType.query.filter_by(
#        product_type_id=product_type_id, domain_id=domain_id).one()
#    product = {
#        'product_id': uuid.uuid4().hex,
#    }
#    # if ProductType object has schema load it
#    if product_type.schema:
#        # we get all fields for this product type
#        product_fields = product_type.schema.get('fields', [])
#        # load all field schemas
#        field_metas = load_field_metas([f['name'] for f in product_fields])
#        # init product fields with info found in field schema
#        product['fields'] = [field_metas[pf['name']].init_schema(pf) 
#                             for pf in product_fields]
#    rv = {
#        'self': url_for(
#            'api.get_product_template', product_type_id=product_type_id),
#        'template': product,
#    }
#    return rv, 200, []

#@route('/product-summary/<product_id>', expects_lang=True)
#def get_product_summary(product_id, lang):
#    record = _get_product(product_id)
#    rv  = _product_summary(record, lang)
#    return rv, 200, []

#@route('/products/<product_id>', expects_lang=True)
#def get_product(product_id, lang):
#    product = _get_product(product_id)
#    rv = {
#        'self': url_for('api.get_product', product_id=product_id),
#        'summary_url': url_for('api.get_product_summary', product_id=product_id),
#        #'caption': _caption(product, lang),
#        'product_id': product_id,
#        'fields': _fields(product.data.get('fields', []), lang),
#    }
#    return rv, 200, []


# TODO: we'll eventually have to revert to this version or something close,
# that is aware of Field schema stored in the database.
#def _merge_fields(productdata, datafields, lang):
#    field_types = {f.name: f.field_type for f in Field.query.all()}
#    for df in datafields:
#        field_type = field_types.get(df.get('name'))
#        if field_type in Field.text_types:
#            df['value'], value = {}, df.get('value') # uploaded value
#            #if product.data and product.data.fields:
#            for pf in productdata['fields']:
#                if pf.get('name')==df['name']:
#                    df['value'] = pf.get('value', {}) # localized values
#            df['value'][lang] = value # merge localized and uploaded value 
#    productdata['fields'] = datafields

#def _fields(fields, lang):
#    if not fields:
#        return []
#    names = [f['name'] for f in fields if f.get('name')]
#    field_metas = load_field_metas(names, g.domain['domain_id'])
#    return [_field(f, field_metas.get(f.get('name')), lang) for f in fields]
#
#def _field(f, meta, lang):
#    rv = dict(
#        name = f.get('name'),
#        #field_type = meta.field_type,
#        #label = meta.schema.get('label', {}).get(lang, None)
#        publish = f.get('publish'),
#        captionable = f.get('captionable'),
#        searchable = f.get('searchable'),
#        meta = {
#            'url': url_for('api.get_field', field_id=clean_uuid(meta.field_id)),
#            'name': f['name'],
#            'field_id': clean_uuid(meta.field_id),
#            'rel': 'FieldMeta',} if meta else None,
#    )
#    if meta and (meta.field_type in Field.text_types):
#        rv['value'] = f.get('value', {}).get(lang)
#    else:
#        rv['value'] = f.get('value', None)
#    return rv


#def hydrate_field(product_field, field):
#    pf = product_field
#    return {
#        'name': pf['name'],
#        'searchable':  pf.get('searchable', False),
#        'publish':  pf.get('publish', False),
#        'value': pf.get('value', None),
#        #'properties': field.schema if field else None,
#    }

