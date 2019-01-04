from . import db

FieldType = db.pg.ENUM(
    'SHORT_TEXT', 
    'MEDIUM_TEXT', 
    'LONG_TEXT',
    'LIST', # via markdown
    'SINGLE_CHOICE',
    'MULTI_CHOICE',
    'BOOL',
    'TABLE',
    'COMPLEX',
    name='field_types'
)

class Field(db.Model, db.TenantMixin): #, FieldInitializerMixin,):
    __abstract__ = False
    __tablename__ = 'fields'

    field_id = db.Column(db.UUID, primary_key=True)
    name = db.Column(db.Unicode, nullable=False)
    field_type = db.Column(FieldType, default='SHORT_TEXT')
    translated = db.Column(db.Boolean, default=True)
    schema = db.Column(db.JSONB)
    """
    schema:
    {
        if field_type in [SHORT_TEXT, MEDIUM_TEXT, LONG_TEXT, LIST]:
        "label": {<lang>: <label>,...},
        if field_type in [SINGLE_CHOICE, MULTI_CHOICE]:
        "label": {<lang>: <label>,...},
        "options": {
            <option_name>: {<lang>: <label>,... },
            ...
        },
        "order": [<option_name>, ...]
    }
    """

    tenant = db.relationship('Tenant')

    text_types = ['SHORT_TEXT', 'MEDIUM_TEXT', 'LONG_TEXT', 'LIST']
    choice_types = ['SINGLE_CHOICE', 'MULTI_CHOICE']

    def get_schema(self, lang):
        if not self.schema:
            return {}

        if self.field_type in self.text_types:
            return TextSchema(self.schema, lang).get_schema()

        if self.field_type=='BOOL':
            return BoolSchema(self.schema, lang).get_schema()

        if self.field_type in self.choice_types:
            return ChoiceSchema(self.schema, lang).get_schema()

    def set_schema(self, data, lang):
        if not self.schema:
            self.schema = {}

        if self.field_type in self.text_types:
            TextSchema(self.schema, lang).set_schema(data)

        if self.field_type=='BOOL':
            #self.set_bool_schema(data, lang)
            BoolSchema(self.schema, lang).set_schema(data)

        if self.field_type in self.choice_types:
            #self.set_choice_schema(data, lang)
            ChoiceSchema(self.schema, lang).set_schema(data)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'name'),
    )


class FieldSchema:

    def __init__(self, schema, lang):
        self.schema = schema
        self.lang = lang

    def _set_label(self, data):
        self.schema.setdefault('label', {})[self.lang] = data.get('label')

    def _get_label(self):
        label = self.schema.get('label', {self.lang: None})
        return label.get(self.lang)


class BoolSchema(FieldSchema):

    def set_schema(self, data): 
        self._set_label(data)
        self._set_default(data)
        self._set_options(data)

    def get_schema(self):
        return {
            'label': self._get_label(),
            'default_value': self.schema.get('default_value', False),
            'options': self._get_options(),
        }

    def _set_default(self, data):
        self.schema['default_value'] = data.get('default_value') is True

    def _set_options(self, data):
        # False is 0 , True is 1
        options = self.schema.get('options')
        if not options:
            options = self.schema['options'] = [{}, {}]
        data_options = data.get('options', [None, None])
        for i, o in enumerate(options):
            try:
                o[self.lang] = data_options[i]
            except (KeyError, AttributeError, TypeError):
                o[self.lang] = None

    def _get_options(self):
        options = self.schema.get('options') 
        if not options:
            options = [{}, {}]
        return [v.get(self.lang) for v in options]


class ChoiceSchema(FieldSchema):

    def set_schema(self, data):
        self._set_label(data)
        self._set_options(data)

    def get_schema(self):
        return {
            'label': self._get_label(),
            'options': self._get_options(),
        }

    def _set_options(self, data):
        existing_options = {o['value']: o['label'] 
                            for o in self.schema.setdefault('options', [])}
        options = []
        for o in data.get('options', []):
            try:
                label = existing_options[o['value']]
                label[self.lang] = o.get('label')
            except KeyError:
                label = {self.lang: o.get('label')}

            options.append({
                'value': o.get('value'),
                'label': label,
                'default_value': o.get('default_value') is True,
            })
        self.schema['options'] = options

    def _get_options(self):
        def _label(o):
            label = o.get('label', {self.lang: None})
            return label.get(self.lang)
        return [{
            'label': _label(o),
            'value': o.get('value'),
            'default_value': o.get('default_value', False),
        } for o in self.schema.get('options', [])]


class TextSchema(FieldSchema):
    def set_schema(self, data):
        self._set_label(data)
        self._set_default(data)

    def get_schema(self):
        return {
            'label': self._get_label(),
            'default_value': self._get_default(),
        }

    def _get_default(self):
        default_value = self.schema.get('default_value', {self.lang: None})
        return default_value.get(self.lang)

    def _set_default(self, data):
        self.schema.setdefault('default_value', {})[self.lang] = data.get(
            'default_value')


class ProductType(db.TenantMixin, db.Model,):
    __tablename__ = 'product_types'

    product_type_id = db.Column(db.UUID, primary_key=True)
    name = db.Column(db.Unicode, nullable=False)
    schema = db.Column(db.JSONB)
    """
    {
        "fields": [
            {"field": <fieldname>, "visible": <bool>, "searchable": <bool>},
            ... 
        ]
    }
    """

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'name'),
    )

    def get_field_value_key(self, field):
        field_type = field.get('field_type', 'SHORT_TEXT').upper()
        single_value_types = ('SINGLE_CHOICE', 'BOOL')
        if field_type in single_value_types:
            return 'value'
            #rv = 'value', field['value']
        else:
            return 'values'
            #rv = 'values', field['values']

