import uuid
import simplejson as json

from flask import redirect, g, current_app as app, abort, url_for
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy import exc as sql_exc
from vino import errors as vno_err

from b2bapi.db import db
from b2bapi.utils.uuid import clean_uuid
from b2bapi.db.models.groups import (
    Group, GroupOption, ProductGroupOption)
from ._route import (
    route, hal, json_abort, domain_owner_authorization as domain_owner_authz,
    account_owner_authorization as account_owner_authz,
)
from .product_utils import _localize_data, _merge_localized_data, _delocalize_data

@route('/groups', expects_domain=True, expects_lang=True, 
       authorize=domain_owner_authz)
def get_groups(lang, domain):
    groups = Group.query.filter_by(domain_id=domain.domain_id).all()
    rv = hal()
    rv._l('self', url_for('api.get_groups'))
    rv._l('productlist:group', url_for('api.get_group', group_id='{group_id}'),
                            templated=True, unquote=True)
    rv._l('productlist:group_resources', url_for('api.get_group_resources'))
    rv._k('group_ids', [g.group_id for g in groups])
    return rv.document, 200, []

@route('/group-resources', expects_domain=True, expects_params=True,
       expects_lang=True, authorize=domain_owner_authz)
def get_group_resources(params, domain, lang):
    group_ids = params.getlist('fid')
    q = Group.query.filter_by(domain_id=domain.domain_id)

    if group_ids:
        q = q.filter(Group.group_id.in_(group_ids))
    groups = q.all()
    rv = hal()
    rv._l('self', url_for('api.get_group_resources'))
    rv._k('group_ids', [g.group_id for g in groups])
    rv._embed('groups', [_group_resource(g, lang) for g in groups])
    return rv.document, 200, []

# TODO: review
@route('/groups', methods=['POST'], expects_domain=True, expects_data=True,
       expects_lang=True, authorize=domain_owner_authz)
def post_group(data, lang, domain):
    #TODO: validate
    # data = val.new_group.validate(data)

    g = Group( domain_id=domain.domain_id)
    g.data = _localize_data(data['data'], ['label', 'description'], lang)
    g.active = data['active']
    g.multichoice = data['multichoice']
    db.session.add(g)

    try:
        db.session.flush()
    except:
        db.session.rollback()
        json_abort(400, {'error': 'Bad format'})


    if data.get('options'):
        _sync_options(g, data['options'], lang, domain.domain_id)
    rv = hal()
    location = url_for('api.get_group', group_id=g.group_id)
    rv._l('location', location)
    rv._k('group_id', g.group_id)
    return rv.document, 201, [('Location', location)]

def _sync_options(g, options, lang, domain_id):
    # first, find all options that did not make it
    try:
        new_option_ids = set(
            [clean_uuid(o['group_option_id']) for o in options if o.get('group_option_id')])
        existing_option_ids = set([clean_uuid(o.group_option_id) for o in g.options])
    except:
        db.session.rollback()
        json_abort(400, {'error': 'group_option_id has an invalid UUID format'})

    deleted = tuple(existing_option_ids.difference(new_option_ids))
    # delete all relations to products
    if deleted:
        clause = db.text(
            'delete from products_group_options '
            'where domain_id=:domain_id '
            'and group_option_id in :optionlist'
        )
        delete_product_options = clause.bindparams(domain_id=domain_id, optionlist=deleted)
        db.session.execute(delete_product_options)
        # delete options
        clause = db.text(
            'delete from group_options '
            'where domain_id=:domain_id '
            'and group_option_id in :optionlist'
        )
        delete_options = clause.bindparams(domain_id=domain_id, optionlist=deleted)
        db.session.execute(delete_options)
    # update the remaining existing options
    for position,o in enumerate(options):
        # if the option has an id it needs to be updated
        if o.get('group_option_id'):
            try:
                # go through existing options
                for fp in g.options:
                    # and find the corresponding option
                    if clean_uuid(fp.group_option_id)==clean_uuid(o['group_option_id']):
                        # update position
                        fp.position = position
                        # merge data
                        _merge_localized_data(
                            fp.data, o.get('data', {}), ['label'], lang)
            except IndexError:
                db.session.rollback()
                json_abort(400, {'error': 'Invalid group_option_id'})
        # if option does not have an id it needs to be added
        else:
            try:
                # new option
                fp = GroupOption(
                    domain_id=domain_id, 
                    position=position,
                )
                # localize the data
                fp.data = _localize_data(
                    o.get('data', {}), ['label'], lang)
                # add to group
                g.options.append(fp)
            except:
                db.session.rollback()
                json_abort(400, {'error': 'Bad format'})

@route('/groups/<group_id>', methods=['PUT'], expects_data=True, 
       expects_lang=True, expects_domain=True, authorize=domain_owner_authz)
def put_group(group_id, data, lang, domain):
    #TODO: validate
    # data = val.edit_group.validate(data)
    g = _get_group(group_id, domain.domain_id)
    _merge_localized_data(g.data, data.pop('data'), ['label', 'description'], lang)
    g.active = data.get('active', False)
    g.multichoice = data.get('multichoice', False)
    _sync_options(g, data.get('options', []), lang, domain.domain_id)
    # TODO: process options in bulk
    try:
        db.session.flush()
    except:
        db.session.rollback()
        json_abort(400, {'error': 'Bad format'})
    return {}, 200, []

def _get_group(group_id, domain_id):
    try:
        return Group.query.filter_by(
            group_id=group_id, 
            domain_id=domain_id
        ).one()
    except: 
        json_abort(404, {'error': 'Group not found'})

def _group_resource(g, lang,):
    rv = hal()
    rv._l('self', url_for('api.get_group', group_id=g.group_id))
    rv._l('options', url_for('api.post_group_option', group_id=g.group_id))
    rv._l('option', url_for('api.get_group_option', group_id=g.group_id,
                            group_option_id='{group_option_id}'),
                            templated=True, unquote=True)
    rv._k('group_id', g.group_id)
    rv._k('active', g.active)
    rv._k('multichoice', g.multichoice)
    rv._k('data', _delocalize_data(g.data, ['label', 'description'], lang))
    rv._k('options', [{
        'data': _delocalize_data(o.data, ['label'], lang),  
        'group_option_id': clean_uuid(o.group_option_id)} for o in g.options])
    return rv.document

@route('/groups/<group_id>', expects_domain=True, expects_lang=True,
       authorize=domain_owner_authz)
def get_group(group_id, lang, domain):
    g = _get_group(group_id, domain.domain_id)
    rv = _group_resource(g, lang)
    return rv, 200, []

@route('/groups/<group_id>', methods=['DELETE'], expects_domain=True,
       authorize=domain_owner_authz)
def delete_group(group_id, domain):
    try:
        db.session.execute(
            'DELETE FROM groups WHERE domain_id=:domain_id ' 
            'AND group_id=:group_id ',
            {
                'domain_id':domain.domain_id, 
                'group_id':group_id,
            })
    except: 
        db.session.rollback()
    return {}, 200, []

def _group_option_resource(group_option, lang):
    f_o = group_option
    rv = hal()
    rv._l('self', url_for('api.get_group_option', group_id=f_o.group_id,
                          group_option_id=f_o.group_option_id))
    rv._l('products', url_for(
        'api.put_group_option_products', group_id=f_o.group_id,
        group_option_id=f_o.group_option_id))
    #if not partial:
    #    rv._l('group', url_for('api.get_group', group_id=f_o.group_id))
    rv._k('group_option_id', f_o.group_option_id)
    rv._k('data', _delocalize_data(f_o.data, ['label'], lang))
    rv._k('products', [p.product_id for p in group_option.products])
    return rv.document

@route('/groups/<group_id>/options', methods=['POST'], expects_lang=True,
       expects_domain=True, expects_data=True, authorize=domain_owner_authz)
def post_group_option(group_id, data, lang, domain):
    # TODO: validation
    # data = val.new_group_option(data)
    f_o = GroupOption(domain_id=domain.domain_id, group_id=group_id)
    f_o.data = _localize_data(data, ['label'], lang)
    db.session.add(f_o)
    try:
        db.session.flush()
    except: 
        db.session.rollback()
        json_abort(400, {'error': 'Bad format'})
    rv = hal()
    location = url_for('api.get_group_option', group_id=group_id, 
                       group_option_id=f_o.group_option_id)
    rv._l('location', location)


def _get_group_option(group_id, group_option_id, domain_id):
    try:
        f_o = GroupOption.query.filter(
            GroupOption.group_id==group_id, 
            GroupOption.group_option_id==group_option_id,
            GroupOption.domain_id==domain_id).one()
        return f_o
    except:
        json_abort(404, {'error': 'Group option not found'})

@route('/groups/<group_id>/options/<group_option_id>', expects_domain=True,
       authorize=domain_owner_authz, expects_lang=True)
def get_group_option(group_id, group_option_id, lang, domain):
    f_o = _get_group_option(group_id, group_option_id, domain.domain_id)
    rv = _group_option_resource(f_o, lang)
    return rv, 200, []

@route('/groups/<group_id>/options/<group_option_id>', expects_domain=True,
       expects_lang=True, expects_data=True, authorize=domain_owner_authz)
def put_group_option(group_id, group_option_id, data, lang, domain):
    # TODO: validate
    # data = val.group_option.validate(data)
    f_o = _get_group_option(group_id, group_option_id, domain.domain_id)
    _merge_localized_data(f_o.data, data['data'], ['label'], lang)
    try:
        db.session.flush()
    except:
        json_abort(400, {'error': 'Bad format'})
    return {}, 200, []

@route('/groups/<group_id>/options/<group_option_id>', expects_domain=True,
       authorize=domain_owner_authz)
def delete_group_option(group_id, group_option_id, domain):
    try:
        db.session.execute(
            'DELETE FROM group_options WHERE domain_id=:domain_id ' 
            'AND group_id=:group_id '
            'AND group_option_id=:group_option_id',
            {
                'domain_id':domain.domain_id, 
                'group_id':group_id,
                'group_option_id':group_option_id
            })
    except: 
        db.session.rollback()
    return {}, 200, []

@route('/groups/<group_id>/options/<group_option_id>/products',
       methods=['PUT'], expects_domain=True, expects_data=True,
       authorize=domain_owner_authz)
def put_group_option_products(group_id, group_option_id, domain, data):
    f_o = _get_group_option(group_id, group_option_id, domain.domain_id)
    try:
        db.session.execute(
            'DELETE FROM products_group_options WHERE domain_id=:domain_id ' 
            'AND group_option_id=:group_option_id',
            {
                'domain_id':domain.domain_id, 
                'group_option_id':group_option_id
            })
    except: 
        db.session.rollback()
        raise
        #json_abort(400, {'error': 'Bad format'})

    new = [{
        'domain_id': domain.domain_id, 
        'group_option_id': group_option_id, 
        'product_id': product_id} for product_id in data.get('products', [])]

    if new:
        db.session.execute(
            'insert into products_group_options '
            '(domain_id, group_option_id, product_id) values '
            '(:domain_id, :group_option_id, :product_id)', new)

    try:
        db.session.flush()
    except:
        db.session.rollback()
    return {}, 200, []

