import uuid
import simplejson as json
import copy

from flask import redirect, g, current_app as app, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db import db
from b2bapi.db.models.products import Product
from b2bapi.db.models.meta import ProductType, Field
from b2bapi.utils.uuid import clean_uuid
from b2bapi.db.schema import generic as product_schema
from ._route import route, json_abort, hal
from .product_utils import (
    _localize_fields, _localized_product_field, patch_record, Mismatch
)
from .images import img_aspect_ratios

from .validation.products import (add_product, edit_product, edit_product_members)

#@route('/products', methods=['GET'], expects_params=True, expects_lang=True)
#def get_products(params, lang):
#    max_id = None
#    min_id = None
#    tenant_id = g.tenant['tenant_id']
#    q = Product.query.filter_by(tenant_id=tenant_id)
#    if params.get('filters'): 
#        filters = json.loads(params['filters'])
#        q = filtered_query(q, [(k,v) for k,v in filters.iteritems()])
#    #_p_order = lambda p: p.data['fields_order'][0]
#    products = q.all()
#    rv = {
#        'self': url_for('api.get_products',**params),
#        'products': [_product_summary(p, lang) for p in products],
#    }
#    return rv, 200, []

@route('/products', expects_params=True, expects_tenant=True,
       authenticate=True, expects_lang=True)
def get_products(params, tenant, lang):
    tenant_id = tenant.tenant_id
    q = Product.query.filter_by(tenant_id=tenant_id)
    #if params.get('filters'): 
    #    filters = json.loads(params['filters'])
    #    q = filtered_query(q, [(k,v) for k,v in filters.iteritems()])
    products = q.all()
    product_url = url_for('api.get_product', product_id='{product_id}')
    rv = hal()
    rv._l('self', url_for('api.get_products', **params))
    rv._l('simpleb2b:product', product_url, unquote=True, templated=True)

    rv._embed('products', [_get_product_resource(p, lang, partial=True)
                           for p in products])
    return rv.document, 200, []

def _product_summary(p, lang):
    return {
        'self': url_for('api.get_product_summary', product_id=p.product_id),
        'product_id': p.product_id.hex,
        #'caption': _caption(p.data, lang),
        'captionable_fields': _caption_fields(p.data['fields'], lang),
        'url': url_for('api.get_product', product_id=p.product_id),
    } 

def _caption_fields(fields, lang):
    rv = []
    for f in fields:
        if f.get('field_type')=='SHORT_TEXT' and f.get('value', {}).get(lang):
            rv.append({'value': f['value'][lang], 'captionable': f.get('captionable')})
    return rv

def _caption(data, lang):
    ''' caption is made of either:
        1- all the fields that have the `captionable` flag
        2- the field with hte `caption` name
        3- the first SHORT_TEXT field
    '''
    rv = ''
    try:
        captionable = []
        named_caption = None
        short_text_caption = None
        for f in data['fields']:
            # only SHORT_TEXT can be part of caption
            if f['field_type']!='SHORT_TEXT':
                continue
            if not short_text_caption:
                short_text_caption = f['value'][lang]
            if not named_caption and f.get('name')=='caption':
                named_caption = f['value'][lang]
            if f.get('captionable') and f['value'][lang]:
                captionable.append(f['value'][lang])
        # TODO: put the separator in a config
        caption = '-'.join(captionable) or named_caption or short_text_caption
        return caption or ''
    except:
        return ''




# TODO: temporarily hardwired 
#@route('/product-templates/<product_type_id>', methods=['GET'])
#def get_product_template(product_type_id):
#    tenant_id = g.tenant['tenant_id']
#    product_type = ProductType.query.filter_by(
#        product_type_id=product_type_id, tenant_id=tenant_id).one()
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

def _get_product(product_id, tenant_id):
    product_id = clean_uuid(product_id)
    try:
        if product_id is None:
            raise orm_exc.NoResultFound()
        return Product.query.filter_by(product_id=product_id, 
                                       tenant_id=tenant_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error': 'Product Not Found'})

@route('/product-summary/<product_id>', expects_lang=True)
def get_product_summary(product_id, lang):
    record = _get_product(product_id)
    rv  = _product_summary(record, lang)
    return rv, 200, []

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

@route('/products/<product_id>', authenticate=True, expects_tenant=True,
       expects_params=True, expects_lang=True)
def get_product(product_id, tenant, params, lang):
    # in the meantime, while waiting for validation
    partial = int(params.get('partial', False))
    product = _get_product(product_id, tenant.tenant_id)
    document = _get_product_resource(product, lang, partial=partial)
    return document, 200, []

def _get_product_resource(p, lang, partial=True):
    rv = hal()
    rv._l('self', url_for('api.get_product', product_id=p.product_id,
                          partial=partial))
    rv._l('images', url_for('api.get_product_images', product_id=p.product_id))
    rv._k('product_id', p.product_id.hex)
    rv._k('visible', p.visible)

    rv._k('images', [img_aspect_ratios(
        i.image, aspect_ratios=['1:1'], sizes=['thumb', 'medium'])
        for i in p.images
    ])

    if partial:
        # we set the `partial` flag on partial representations. HAL allows
        # for some inconsistencies between representations of the same 
        # resource. 
        rv._k('partial', partial)

        # we only get the first 3 fields if it's a partial product resource
        # we're fetching
        fields = [_localized_product_field(f, lang)
                        for f in p.data.setdefault('fields', [])[:3]]
    else:
        # we get all fields for a non-partial representation
        fields = [_localized_product_field(f, lang) 
                         for f in p.data.setdefault('fields', [])]
        # NOTE: maybe we'll add this at some point
        #rv._k('unit_price', p.data.get('unit_price'))
        #rv._k('quantity_unit', p.data.get('quantity_unit'))
        # TODO:
        #rv._embed('filters', [_get_filter_resource(f, True) for f in p.filters])

    rv._k('data', {'fields': fields})
    return rv.document

def _fields(fields, lang):
    if not fields:
        return []
    names = [f['name'] for f in fields if f.get('name')]
    field_metas = load_field_metas(names, g.tenant['tenant_id'])
    return [_field(f, field_metas.get(f.get('name')), lang) for f in fields]

def _field(f, meta, lang):
    rv = dict(
        name = f.get('name'),
        #field_type = meta.field_type,
        #label = meta.schema.get('label', {}).get(lang, None)
        publish = f.get('publish'),
        captionable = f.get('captionable'),
        searchable = f.get('searchable'),
        meta = {
            'url': url_for('api.get_field', field_id=clean_uuid(meta.field_id)),
            'name': f['name'],
            'field_id': clean_uuid(meta.field_id),
            'rel': 'FieldMeta',} if meta else None,
    )
    if meta and (meta.field_type in Field.text_types):
        rv['value'] = f.get('value', {}).get(lang)
    else:
        rv['value'] = f.get('value', None)
    return rv


def load_field_metas(schema_names, tenant_id):
    # query the db for fields with those names and produce
    # a dict indexed by those names
    fields = Field.query.filter(Field.tenant_id==tenant_id, 
                                Field.name.in_(schema_names)).all()
    return {f.name:f for f in fields}


def hydrate_field(product_field, field):
    pf = product_field
    return {
        'name': pf['name'],
        'searchable':  pf.get('searchable', False),
        'publish':  pf.get('publish', False),
        'value': pf.get('value', None),
        #'properties': field.schema if field else None,
    }



def populate_product(product, data, lang):
    for k,v in data.items():
        if k=='data':
            for data_key, data_value in v.items():
                if data_key=='fields':
                    # we merge fields data
                    _merge_fields(product.data, data_value, lang)
                else:
                    # we simply overwrite other data
                    product.data[data_key] = data_value
        else:
            setattr(product,k,v)

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


def _merge_fields(productdata, datafields, lang):
    # loop through the uploaded fields
    for df in datafields:
        # if field is a text type
        if df['field_type'] in Field.text_types:
            # extract the uploaded value and reset the field value
            # to an empty dict, ready to take localized values
            df['value'], value = {}, df.get('value')

            # now we search if the product already has an existing field with
            # the same name
            for pf in productdata['fields']:
                # if we find a matching field we give its (localized) value
                # to our just uploaded field's value
                if pf.get('name')==df['name']:
                    df['value'] = pf.get('value', {})
            # now whether the field was already present or not
            # we set the uploaded value as a localized value
            df['value'][lang] = value

    # we're now ready to replace the old fields with the new data set
    productdata['fields'] = datafields


def db_flush():
    try:
        db.session.flush()
    except sql_exc.IntegrityError as e:
        db.session.rollback()
        json_abort(400, {'error': 'Problem while saving data'})

@route('/products', methods=['POST'], expects_data=True, expects_lang=True)
def post_product(data, lang):
    try:
        data = add_product.validate(data)
    except vno_err.ValidationErrorStack as e:
        json_abort(400, {'error': 'Invalid data ' + str(e)})
    p = Product(data={'fields': []})
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
       authenticate=True, expects_tenant=True, expects_lang=True)
def put_product(product_id, data, tenant, lang):
    data = edit_product.validate(data)
    p = _get_product(product_id, tenant.tenant_id)
    populate_product(p, data, lang)

    #filters = data.pop('filters', [])
    #data.pop('data', None)
    #p.populate(**data)

    #try:
    #    for i,f in enumerate(fields):
    #        try:
    #            val = p.data.setdefault('fields', [])[i]
    #            val['en'] = f
    #        except IndexError:
    #            val = {'en': f}
    #            p.data.setdefault('fields', []).append(val)
    #except:
    #    json_abort(400, {'error':'Bad Format'})

    #p.filters = Filter.query.filter(Filter.filter_id.in_(filters)).all()

    db_flush()
    return {}, 200, []

"""
For a data to be patched to the product, it must already be present. 
"""
@route('/products/<product_id>', methods=['PATCH'], expects_data=True,
       expects_tenant=True, expects_lang=True, authenticate=True)
def patch_product(product_id, data, tenant, lang):
    #data = edit_product_members.validate(data)
    p = _get_product(product_id, tenant.tenant_id)
    try:
        _localize_fields(data, lang)
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
        #    (products.c.tenant_id==g.tenant['tenant_id'])&
        #    (products.c.product_id==product_id)))
    except:
        pass
    return ({}, 200, [])


def filtered_query(q, filters):
    filter_path = 'data#>\'{{fields,{name},value}}\''
    text_filter = '{} @> \'"{{value}}"\''.format(filter_path)
    bool_filter = '{} @> \'{{value}}\''.format(filter_path)

    for n,v in filters:
        if v in (True,False):
            v = str(v).lower()
            q = q.filter(db.text(bool_filter.format(name=n, value=v)))
        else:
            q = q.filter(db.text(text_filter.format(name=n, value=v)))
    return q


