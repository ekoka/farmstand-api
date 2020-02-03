from vino.api.schema import obj, arr, prim
from vino.processors import validating as vld
from vino import errors as vno_err
from b2bapi.utils import password as pwd 

from . import (set_domain, check_uuid4,  set_uuid, upper, remove, set_value,
               ExtraProperties)


def check_at_least_one_signin_present(data, state):
    if not data.get('email') and not data.get('google_signin'):
        raise vno_err.ValidationError(
            'A signin option is required to create a new account.')
    return data

def check_email_format(data, state):
    if not '@' in data:
        raise vno_err.ValidationError('Email format does not seem valid')
    return data

remove_extra_props = ExtraProperties('remove')

password_check = prim(
    ~vld.required,
    vld.rejectempty(failsafe=remove), # if we receive empty string remove it
    vld.rejectnull(failsafe=remove), # if we receive null remove it
    pwd.max_size(200),
    pwd.min_size(8),
    pwd.padless_size(6),
    pwd.dictionary_match, # john the ripper
    pwd.alphanum_sequence(minlength=30),
    pwd.repeated_char(minlength=50),
)

def rename(old_name, new_name):
    def processor(data, state):
        try:
            data[new_name] = data.pop(old_name)
        except KeyError:
            raise
        return data
    return processor

new_account_via_google = obj(
    prim(vld.required, vld.rejectnull, vld.rejectempty).apply_to('email'),
    prim(vld.optional(default=set_value(None)), vld.allownull, vld.allowempty).apply_to(
        'given_name', 'family_name',), 
    prim(vld.optional(default=set_value(False)), 
         vld.rejectnull(failsafe=set_value(False)),
         vld.rejectempty(failsafe=set_value(False))).apply_to(
            'email_verified'),
    prim(vld.optional(default=set_value('en')), 
         vld.rejectempty(failsafe=set_value('en')),
         vld.rejectnull(failsafe=set_value('en')),).apply_to(
             'locale'),
    remove_extra_props, 
    # make sure to put these after the remove_extra_props directive 
    # otherwise the renamed fields will be removed
    rename('locale', 'lang'),
    rename('given_name', 'first_name'),
    rename('family_name', 'last_name'),
    rename('email_verified', 'confirmed'),
)

new_account_via_email = obj(
    prim(vld.required, vld.rejectnull, vld.rejectempty, check_email_format).apply_to(
             'email'),
    password_check.apply_to(
        'password'),
    prim(vld.optional(default=set_value(None)), 
         vld.rejectempty(failsafe=set_value(None))).apply_to(
        'first_name', 'last_name'), 
    # set `confirm` to false no matter what
    prim(vld.optional(override=set_value(False))).apply_to('confirmed'),
    prim(vld.optional(default=set_value('en')), # if nothing is received set to 'en' 
        # if value is empty at this point, set to 'en'
         vld.rejectempty(failsafe=set_value('en')), 
         # if value is null at this point, set to 'en' 
         vld.rejectnull(failsafe=set_value('en'))).apply_to('lang'),
    remove_extra_props,
)

edit_account = obj(
    prim(vld.optional, vld.allowempty).apply_to('first_name'),
    prim(vld.optional, vld.allowempty).apply_to('last_name'),
    obj(~vld.required, vld.rejectnull(failsafe=remove), vld.allowempty,
        prim(~vld.required, vld.allowempty).apply_to(
            'phone', 'organization', 'role', 'website', 'bio', 'public_name',
            'location', 'linkedin', 'facebook', 'skype', 'whatsapp',
        ), 
        remove_extra_props,
    ).apply_to('data'),
    remove_extra_props,
)

add_product_type = obj(
    prim(~vld.required, remove).apply_to('self'),
    prim(vld.required(override=set_domain)).apply_to('domain_id'),
    prim(vld.required(default=set_uuid), 
         vld.rejectnull(failsafe=set_uuid),
         check_uuid4,).apply_to(
        'product_type_id'),
    prim().apply_to('name'),
    obj(arr(obj().apply_to(30)).apply_to('fields')).apply_to('schema'),
)

edit_product_type = obj(
    prim(~vld.required, remove).apply_to('self'),
    prim(~vld.required, remove).apply_to('product_type_id', 'domain_id'),
    prim().apply_to('name'),
    obj(arr(obj().apply_to(30)).apply_to('fields')).apply_to('schema'),
)
