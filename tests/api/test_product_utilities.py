import pytest
from appsrc.api.product_utils import (
    _localize_fields, appendobj, patch_record, Mismatch)
from appsrc.db.models.meta import Field

def test_text_fields_are_localized():
    val1 = 'val1'
    val2 = 'val2'
    for ft in Field.text_types:
        data = {
            'data': {
                'fields': [
                    {'value': val1, 'field_type': ft},
                    {'value': val2, 'field_type': ft},
                ]
            }
        }
        _localize_fields(data, 'gb')
        # all test fields are now localized
        assert val1==data['data']['fields'][0]['value']['gb']
        assert val2==data['data']['fields'][1]['value']['gb']

def test_only_text_fields_are_localized():
    val1 = 'val1'
    val2 = 'val2'
    val3 = 'val3'
    for ft in Field.text_types:
        data = {
            'data': {
                'fields': [
                    {'value': val1, 'field_type': 'BOOL'},
                    {'value': val2, 'field_type': 'MULTI_CHOICE'},
                    {'value': val3, 'field_type': 'text'},
                ]
            }
        }
        result = _localize_fields(data, 'gb')
        # all test fields stayed the same
        assert val1==data['data']['fields'][0]['value']
        assert val2==data['data']['fields'][1]['value']
        assert val3==data['data']['fields'][2]['value']

@pytest.fixture
def cls():
    class C:
        def __init__(s, **kw):
            for k,v in kw.items():
                setattr(s, k, v)
    return C


def test_appendobj_appends_to_proper_location_with_keymap(cls):
    data = {'fields': [
        {'value': [{}, {}]}
    ]}
    obj = cls(data=data, visible=True, product_id=883)

    keymap = ['data', 'fields', 0, 'value']
    foo = {'value': 'abc'}
    appendobj(obj, keymap, foo)
    assert obj.data['fields'][0]['value'][-1] is foo

def test_patch_record_can_set_field_value(cls):
    obj = cls(field1=True, field2='abc', field3='foo')
    data = {
        'field1': False,
        'field2': 'xyz',
        'field3': 'bar',
    }
    patch_record(obj, data)
    assert obj.field1==data['field1']
    assert obj.field2==data['field2']
    assert obj.field3==data['field3']


def test_patch_record_raises_Mismatch_error_on_non_existing_value(cls):
    obj = cls(field1=True, field2='abc', field3='foo')
    data = {
        'field1': False,
        'field2': 'xyz',
        'field3': 'bar',
        'field4': 'baz',
    }
    with pytest.raises(Mismatch) as e:
        patch_record(obj, data)
    e_str = str(e.value).lower()
    assert 'invalid attribute' in e_str
    assert 'field4' in e_str

def test_patch_record_can_set_existing_json_value(cls):
    obj = cls(field1=True, field2={'foo': 'bar'}, field3='foo')
    data = {
        'field2': {'foo': 'baz'},
    }
    patch_record(obj, data)
    assert obj.field2['foo']=='baz'

def test_patch_record_can_set_new_json_value(cls):
    obj = cls(field1=True, field2={}, field3='foo')
    data = {
        'field2': {'foo': 'baz'},
    }
    patch_record(obj, data)
    assert obj.field2['foo']=='baz'

def test_patch_record_can_set_inner_value_in_dict(cls):
    obj = cls(field1=True, field2={'outer': {'inner': 'bar'}}, field3='foo')
    data = {
        'field2': {'outer': {'inner': 'baz'}},
    }
    patch_record(obj, data)
    assert obj.field2['outer']['inner']=='baz'

def test_patch_record_can_set_data_in_list_of_named_dict(cls):
    obj = cls(
        field1=True,
        field2={'list': [
            {'name': 'dict1', 'key': 'value1'},
            {'name': 'dict2', 'key': 'value2'},
            {'name': 'dict3', 'key': 'value3'},
        ]},
        field3='foo'
    )
    data = {
        'field2': {'list': [
            {'name': 'dict2', 'key': 'bar'},
            {'name': 'dict1', 'key': 'baz'},
        ]}
    }
    patch_record(obj, data)
    assert obj.field2['list'][1]['key']=='bar'
    assert obj.field2['list'][0]['key']=='baz'

def test_change_in_list_of_named_dict_only_affects_specified_names(cls):
    obj = cls(
        field1=True,
        field2={'list': [
            {'name': 'dict1', 'key': 'value1'},
            {'name': 'dict2', 'key': 'value2'},
            {'name': 'dict3', 'key': 'value3'},
        ]},
        field3='foo'
    )
    data = {
        'field2': {'list': [
            {'name': 'dict2', 'key': 'bar'},
            {'name': 'dict1', 'key': 'baz'},
        ]}
    }
    patch_record(obj, data)
    assert obj.field2['list'][2]['key']=='value3'

def test_change_to_named_dict_affects_only_changed_attributes(cls):
    obj = cls(
        field1=True,
        field2={'list': [
            {'name': 'dict1', 'key': 'value1', 'alpha': 'tango'},
            {'name': 'dict2', 'key': 'value2', 'papa': 'charlie'},
            {'name': 'dict3', 'key': 'value3'},
        ]},
        field3='foo'
    )
    data = {
        'field2': {'list': [
            {'name': 'dict2', 'key': 'bar'},
            {'name': 'dict1', 'key': 'baz'},
        ]}
    }
    patch_record(obj, data)
    assert obj.field2['list'][0]['alpha']=='tango'
    assert obj.field2['list'][1]['papa']=='charlie'

def test_new_key_is_added_to_named_dict(cls):
    obj = cls(
        field1=True,
        field2={'list': [
            {'name': 'dict1', 'key': 'value1', 'alpha': 'tango'},
        ]},
        field3='foo'
    )
    data = {
        'field2': {'list': [
            {'name': 'dict1', 'key': 'baz', 'beta': 'romeo'},
        ]}
    }
    patch_record(obj, data)
    assert obj.field2['list'][0]['alpha']=='tango'
    assert obj.field2['list'][0]['key']=='baz'
    assert obj.field2['list'][0]['beta']=='romeo'

def test_new_object_appended_to_dict_list_if_name_not_found(cls):
    obj = cls(
        field1=True,
        field2={'list': [
            {'name': 'dict1', 'key': 'value1', 'alpha': 'tango'},
            {'name': 'dict2', 'key': 'value2', 'beta': 'zeta'},
        ]},
        field3='foo'
    )
    data = {
        'field2': {'list': [
            {'name': 'dict3', 'foo': 'bar', 'papa': 'romeo'},
        ]}
    }
    patch_record(obj, data)
    assert obj.field2['list'][2] is data['field2']['list'][0]

def test_missing_name_field_raises_error_for_list_of_dicts(cls):
    obj = cls(
        field1=True,
        field2={
            'outer': {'inner': 'bar', 'list': None},
        },
        field3={'outer': {'inner': []}},
        field4='abc',
        field5='xyz',
    )
    unnamed = [{'value': 'baz'}]
    data = {
        # no identifier field (name)
        'field3': {'outer': {'inner': unnamed}},
    }
    with pytest.raises(Mismatch) as e:
        patch_record(obj, data)
    assert 'missing identifier' in str(e.value).lower()

def  test_dict_cannot_be_part_of_items_in_ordinary_list(cls):
    obj = cls(
        field3={'outer': {'inner': []}},
    )
    l = ['a', 'b', {'value': 'baz'}]
    data = {
        # no identifier field (name)
        'field3': {'outer': {'inner': l}},
    }
    with pytest.raises(Mismatch) as e:
        patch_record(obj, data)
    assert 'badly formed data' in str(e.value).lower()

def test_ordinary_items_cannot_be_part_of_items_in_dict_list(cls):
    obj = cls(
        field1=True,
        field2={
            'outer': {'inner': 'bar', 'list': None},
        },
        field3={'outer': {'inner': []}},
        field4='abc',
        field5='xyz',
    )
    objlist = [{'value': 'baz', 'name': 'foo'}, True, 'a']
    data = {
        # no identifier field (name)
        'field3': {'outer': {'inner': objlist}},
    }
    with pytest.raises(Mismatch) as e:
        patch_record(obj, data)
    assert 'badly formed data' in str(e.value).lower()

def test_list_of_ordinary_values_set_as_values(cls):
    ordinary_list = list('abcde')
    obj = cls(
        field1=True,
        field2={'list': None, 'foo': 'bar'},
        field3='foo'
    )
    data = {
        'field2': {'list': ordinary_list}
    }
    patch_record(obj, data)
    assert obj.field2['list'] is ordinary_list
    assert obj.field2['foo']=='bar'

def test_nested_lists_are_treated_as_ordinary_values(cls):
    ordinary_list = ['a', 'c', 'd', list('sdfds')]
    obj = cls(
        field1=True,
        field2={'list': None, 'foo': 'bar'},
        field3='foo'
    )
    data = {
        'field2': {'list': ordinary_list}
    }
    patch_record(obj, data)
    assert obj.field2['list'] is ordinary_list
    assert obj.field2['foo']=='bar'


def test_patch_record_doesnt_mess_with_unmodified_data(cls):
    obj = cls(
        field1=True,
        field2={
            'outer': {'inner': 'bar', 'list': None},
        },
        field3={'outer': {'inner': [
            {'name': 'n1', 'value': 'foo'},
            {'name': 'n2', 'value': 'bar'},
        ]}},
        field4='abc',
        field5='xyz',
    )
    data = {
        'field2': {'outer': {'inner': 'baz', 'list': ['a', 'b', 'c']}},
        'field3': {'outer': {'inner': [{'name': 'n1', 'value': 'baz'}]}},
    }
    patch_record(obj, data)
    assert obj.field4=='abc'
    assert obj.field2['outer']['list'][1]=='b'
    assert obj.field3['outer']['inner'][0]['value']=='baz'
    assert obj.field3['outer']['inner'][1]['value']=='bar'
