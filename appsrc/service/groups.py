from ..db import db
from ..db.models.groups import Group, GroupOption
from ..utils.uuid import clean_uuid
#from ..db.data_utils.products import _localize_data, _merge_localized_data
from .product_utils import _localize_data, _merge_localized_data

from . import errors as err

def get_groups(lang, domain):
    # service
    return Group.query.filter_by(domain_id=domain_id).all()

def get_group_resources(domain_id, group_ids):
    # service
    q = Group.query.filter_by(domain_id=domain_id)
    if group_ids:
        q = q.filter(Group.group_id.in_(group_ids))
    return q.all()

# TODO: review
def create_group(domain_id, data, lang):
    # service
    # TODO: validation
    # data = val.new_group.validate(data)
    grp = Group(domain_id=domain_id)
    grp.data = _localize_data(data['data'], ['label', 'description'], lang)
    grp.active = data['active']
    grp.multichoice = data['multichoice']
    db.session.add(grp)
    try:
        db.session.flush()
    except:
        db.session.rollback()
        raise err.FormatError('Could not create group')
    if data.get('options'):
        _sync_options(grp, data['options'], lang, domain_id)
    return grp

def _sync_options(grp, options, lang, domain_id):
    # service
    # first, find all options that did not make it
    try:
        new_option_ids = set(
            clean_uuid(o['group_option_id']) for o in options if o.get('group_option_id'))
        existing_option_ids = set(clean_uuid(o.group_option_id) for o in grp.options)
    except:
        db.session.rollback()
        raise err.FormatError('group_option_id has an invalid UUID format')
    deleted = tuple(existing_option_ids.difference(new_option_ids))
    # delete all relations to products
    if deleted:
        clause = db.text(
            'delete from products_group_options '
            'where domain_id=:domain_id '
            'and group_option_id in :optionlist')
        delete_product_options = clause.bindparams(domain_id=domain_id, optionlist=deleted)
        db.session.execute(delete_product_options)
        # delete options
        clause = db.text(
            'delete from group_options '
            'where domain_id=:domain_id '
            'and group_option_id in :optionlist')
        delete_options = clause.bindparams(domain_id=domain_id, optionlist=deleted)
        db.session.execute(delete_options)
    # update the remaining existing options
    for position,o in enumerate(options):
        # if the option has an id it needs to be updated
        if o.get('group_option_id'):
            try:
                # go through existing options
                for fp in grp.options:
                    # skip irrelevant options
                    if clean_uuid(fp.group_option_id)!=clean_uuid(o['group_option_id']):
                        continue
                    # update position
                    fp.position = position
                    # merge data
                    _merge_localized_data(fp.data, o.get('data', {}), ['label'], lang)
            except IndexError:
                db.session.rollback()
                raise err.FormatError('Invalid group_option_id')
            continue
        # if option does not have an id it needs to be added
        try:
            # new option
            fp = GroupOption(domain_id=domain_id, position=position)
            # localize the data
            fp.data = _localize_data(o.get('data', {}), ['label'], lang)
            # add to group
            grp.options.append(fp)
        except:
            db.session.rollback()
            raise err.FormatError('Bad format')

def update_group(group_id, domain_id, data, lang):
    # service
    #TODO: validate
    # data = val.edit_group.validate(data)
    grp = get_group(group_id, domain_id)
    _merge_localized_data(grp.data, data.pop('data'), ['label', 'description'], lang)
    grp.active = data.get('active', False)
    grp.multichoice = data.get('multichoice', False)
    _sync_options(grp, data.get('options', []), lang, domain_id)
    # TODO: process options in bulk
    try:
        db.session.flush()
    except:
        db.session.rollback()
        raise err.FormatError('Bad format')
    return grp

def get_group(group_id, domain_id):
    # service
    try:
        return Group.query.filter_by(group_id=group_id, domain_id=domain_id).one()
    except:
        raise err.NotFound('Group not found')

def delete_group(group_id, domain_id):
    # service
    try:
        db.session.execute(db.text(
            'DELETE FROM groups WHERE domain_id=:domain_id AND group_id=:group_id '),
            {'domain_id':domain_id, 'group_id':group_id,})
    except:
        db.session.rollback()

def create_group_option(group_id, domain_id, data, lang):
    # service
    # TODO: validation
    # data = val.new_group_option(data)
    g_o = GroupOption(domain_id=domain_id, group_id=group_id)
    g_o.data = _localize_data(data, ['label'], lang)
    db.session.add(g_o)
    try:
        db.session.flush()
    except:
        db.session.rollback()
        raise err.FormatError('Could not create group')
    return g_o

def get_group_option(group_id, group_option_id, domain_id):
    # service
    try:
        return GroupOption.query.filter(
            GroupOption.group_id==group_id,
            GroupOption.group_option_id==group_option_id,
            GroupOption.domain_id==domain_id).one()
    except:
        raise err.NotFound('Group option not found')

def update_group_option(group_id, group_option_id, domain_id, data, lang):
    # service
    # TODO: validate
    # data = val.group_option.validate(data)
    g_o = get_group_option(group_id, group_option_id, domain_id)
    _merge_localized_data(g_o.data, data['data'], ['label'], lang)
    try:
        db.session.flush()
    except:
        raise err.FormatError('Could not update group option')
    return g_o

def delete_group_option(group_id, group_option_id, domain_id):
    # service
    try:
        db.session.execute(db.text(
            'DELETE FROM group_options WHERE domain_id=:domain_id AND group_id=:group_id '
            'AND group_option_id=:group_option_id'), {
                'domain_id':domain_id,
                'group_id':group_id,
                'group_option_id':group_option_id })
    except:
        db.session.rollback()

def update_group_option_products(group_id, group_option_id, domain_id, data):
    # service
    g_o = get_group_option(group_id, group_option_id, domain_id)
    try:
        q = db.text(
            'DELETE FROM products_group_options WHERE domain_id=:domain_id '
            'AND group_option_id=:group_option_id')
        db.session.execute(q, {'domain_id':domain_id, 'group_option_id':group_option_id})
    except:
        db.session.rollback()
        raise err.FormatError('Bad format')
    new = [{
        'domain_id': domain_id,
        'group_option_id': group_option_id,
        'product_id': product_id} for product_id in data.get('products', [])]
    if new:
        q = db.text(
            'INSERT INTO products_group_options (domain_id, group_option_id, product_id) '
            ' values (:domain_id, :group_option_id, :product_id)')
        db.session.execute(q, new)
    try:
        db.session.flush()
    except:
        db.session.rollback()
        raise err.FormatError('Could not associate group option with products')
    return g_o
