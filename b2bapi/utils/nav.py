import re
from collections import OrderedDict
"""
a menu has many items

item:
- has an unique and preferably descriptive id. e.g. main_nav_users, item_users, level_1_users etc...

- belongs to only one menu

- has an url. e.g. "/admin/users"

- has an optional set of additional url patterns that could also "activate" it (without necessarily be its own). For the purpose of this article I'm using a pseudo pattern syntax in my examples, but feel free to use plain ol' regex in your own implementation. e.g. ['/admin/users/<int:id>', '/admin/groups/<anything>']
If a request matching these patterns is sent, this item will also be flagged as active.

- an optional set of *linked submenus*.
"""

def any_converter(var, args):
    template = r'(?P<{var}>{pattern})'
    pattern = '|'.join((x.strip() for x in args.split(',')))
    return template.format(var=var, pattern=pattern)

def static_converter(var):
    template = r'(?P<{var}>.*)'
    return template.format(var=var)

def regex_repl(m):
    conv = m.group('conv')
    args = m.group('args')
    var = m.group('var')

    if not conv:
        return static_converter(var)
    elif conv=='any':
        return any_converter(var, args)

def template_repl(m):
    conv = m.group('conv')
    args = m.group('args')
    var = m.group('var')

    return '{{{var}}}'.format(var=var)

def precompile(route):
    pattern = re.compile(r'''
        <
        (?:                                     # open converter
            (?P<conv>[a-zA-Z_][a-zA-Z0-9_]*)    # converter's name
            (?:\((?P<args>.*?)\))?              # converter's args 
        :                                       # separator
        )                                       # close converter
        ?                                       # converter is optional
        (?P<var>[a-zA-Z_][a-zA-Z0-9_]*)         # variable
        >
    ''', re.I|re.X)

    regex = pattern.sub(regex_repl, route)
    template = pattern.sub(template_repl, route)
    return regex, template


    #match_list = pattern.findall(route)   
    #return route

def url_matches_route(url, route):
    pattern = re.compile(route)
    return pattern.match(url)

def deactivate_all(items):
    for i in items:
        i.active = False
        if i.items: # this is in fact a menu
            deactivate_all(i.items)

def setup_menus(config):
    menus = {}
    for menuid, conf in config.iteritems():
        menus[menuid] = menu = Menu(menuid)
        try:
            menu.items = OrderedDict(
                [(menuitem_conf['id'], MenuItem(menu, **menuitem_conf)) 
                    for menuitem_conf in conf])
        except:
            raise
            # TODO: meaningful error for menuitem['id']
            pass
    return menus

def setup_routes(menus):
    routes = {}
    for m, menu in menus.iteritems():
        for idx, item  in menu.items.iteritems():
            if item.url:
                pattern = '^' + item.url + '/?$'
                routes.setdefault(pattern, set()).add(item)
            if item.urls:
                [routes.setdefault(url, set()).add(item) 
                 for url in item.urls]
    return routes

def link_submenus(menus):
    for menu in menus.values():
        for idx, item in menu.items.iteritems():
            #i.submenus = {sm:menus[sm] 
            #              for sm in i.config.get('submenus', [])}
            item.submenus = {}
            for sm in item.config.get('submenus', []):
                try:
                    item.submenus[sm] = menus[sm]
                    menus[sm].parents[item.id] = item
                except:
                    #TODO: better error for menus[sm]
                    raise

class MenuMapper(object):

    menus = None
    routes = None

    def __init__(self, config):
        self.menus = setup_menus(config)
        self.routes = setup_routes(self.menus)
        link_submenus(self.menus)            

    def resolve_route(self, url):
        for route, items in self.routes.iteritems():
            if url_matches_route(url, route):
                [item.activate() for item in items]

    def deactivate_all(self, items):
        for i in items:
            i.active = False
            if i.items: # this is in fact a menu
                self.deactivate_all(i.items)

class Menu(object):
    id = None
    parents = None
    items = None
    active = False

    def __init__(self, id):
        self.id = id 
        self.parents = {}

    def activate(self):
        if not self.active:
            self.active = True
            if self.parents:
                [parent.activate() for parent in self.parents.values()]


class MenuItem(object):

    id = None
    config = None
    label = None
    url = None
    urls = None
    submenus = None
    menu = None
    items = None
    active = False

    def __init__(self, menu, **config):
        self.config = config
        [setattr(self, k, config.get(k)) for k in (
            'id', 'menu', 'label', 'url', 'urls',)]

        self.url, self.template_url = precompile(self.url)
        self.urls = [precompile(u)[0] for u in self.urls]

    def activate(self):
        if not self.active:
            self.active = True
            if self.menu:
                self.menu.activate()

    def resolve_url(self, **kwargs):
        rv = self.template_url.format(**kwargs)
        if re.compile(self.url).match(rv):
            return rv
        raise Exception('resulting url does not match the template')

def menumapper(config):
    # TODO: handle filesys path
    # support for yaml with json being a subset
    return MenuMapper(config)
