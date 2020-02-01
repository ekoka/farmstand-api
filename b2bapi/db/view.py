from sqlalchemy import exc, orm, schema, event
from sqlalchemy.ext.compiler import compiles

class CreateView(schema.DDLElement):
    def __init__(self, name, selectable):
        self.name = name 
        self.selectable = selectable
# making this specific to postgresql
@compiles(CreateView, 'postgresql')
def visit_pg_create_view(element, compiler):
    template = "CREATE OR REPLACE VIEW {name} AS {select};"
    select = compiler.sql_compiler.process(element.selectable, 
                                           literal_binds=True)
    rv = template.format(name=element.name, select=select)
    return rv

class DropView(schema.DDLElement):
    def __init__(self, name):
        self.name = name 
@compiles(DropView, 'postgresql')
def visit_pg_drop_view(element, compiler):
    return "DROP VIEW IF EXISTS {name};".format(name=element.name)

def create_view(view_name, query, metadata):
    CreateView(view_name, query).execute_at('after_create', metadata)
    DropView(view_name).execute_at('before_drop', metadata)

def view_mapper(view_name, query, metadata, ViewModel, *columns):
    create_view(view_name, query, metadata)

    def view_mapping(metadata, connection, **kw):
        args = (view_name, metadata)
        if columns: 
            args = args + columns
        # enclosing the following in a try/except to catch errors related
        # to additional runs of this mapping. e.g. during migration
        # where the metadata first drops all tables then recreates them
        # issuing an additional 'after-create' event which calls this
        # function into action and attempts to reassociates a `Table` to 
        # the underlying `view_name` view again.
        try:
            reflected_view = schema.Table(*args, **{'autoload_with':connection})
            orm.mapper(ViewModel, reflected_view)
            # removing the `Table` object from the metadata's table list
            # otherwise, when issuing a `metadata.drop_all()` call a DROP
            # TABLE statement on `view_name` will be attempted (instead of the
            # more appropriate DROP VIEW).
            metadata.remove(reflected_view)
        except exc.ArgumentError:
            # we simply ignore additional calls to the mapper
            pass

    event.listen(metadata, 'after_create', view_mapping)
