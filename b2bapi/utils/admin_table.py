import re
from collections import namedtuple


def init_mappings(mappings):
    for table_name, m in mappings.iteritems():
        if not m.get('default_ordering'):
            m['default_ordering'] = m['columns'][0]['name']

        if m['default_ordering'] not in [c['name'] for c in m['columns']]:
            raise Exception('declared Default Column {} does not match listed '
                            'columns'.format(m['default_ordering']))
        if not m['pattern']:
            # TODO more descriptive error
            raise Exception('empty url pattern')
        for c in m['columns']:
            if not c.get('default_sorting'):
                c['default_sorting'] = 'asc'
            if c['default_sorting'] not in ('asc','desc'):
                raise Exception('invalid sorting method: {sorting}'.format(
                    sorting=c['default_sorting']))
    return mappings

class AdminTableMapper(object):
    def __init__(self, name, mapping, order_by=None, sorting=None):
        self.name = name 
        self.mapping = mapping
        order_by = order_by or mapping['default_ordering']
        self.order_by = [c for c in mapping['columns'] 
                       if c['name']==order_by][0]
        self.sorting = sorting or self.order_by['default_sorting']

    def resolve_order_column(self, Model):
        #return Model.product_id.desc()
        column = getattr(Model, self.order_by['name'])
        # sorting method
        sorting = getattr(column, self.sorting)
        # apply sorting
        return sorting()

    @property
    def url_params(self):
        rv = {'order_by': self.order_by['name'], 'sorting': self.sorting}
        return rv

table_context = namedtuple('table_context', 'name mapping order_by sorting')
# TODO this should be loaded into g through some prerequest callback
def get_admin_table_context(mappings, request):
    for mname, m in mappings.iteritems():
        if re.search(m['pattern'], request.path):
            order_by = request.args.get('order_by', None)
            sorting = request.args.get('sorting', None)
            return AdminTableMapper(
                name=mname, mapping=m, order_by=order_by, sorting=sorting)

def column_generator(mappings, name, previous_table=None):
    mapping = mappings[name]
    # are we loading the same table as previous request
    #admin_table = getattr(g, 'admin_table', None)
    pt = previous_table
    sametable = True if pt and (name==pt.name) else False

    for c in mapping['columns']:
        _c = dict(
            name=c['name'],
            sorting=c['default_sorting'],
            label=c.get('label', ''),
        )
        if sametable and c['name']==pt.order_by['name']: # same column
            # reverse the sorting direction 
            _c['sorting'] = {'asc': 'desc', 'desc':'asc'}[pt.sorting]
        yield _c
