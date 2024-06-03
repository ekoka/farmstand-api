from urllib import parse
class Resource:
    document = None

    def __init__(self, hal_or_document=None):
        if hal_or_document is None:
            self.document = {}
            return
        try:
            document = hal_or_document.document
        except AttributeError as e:
            document = hal_or_document
        self.document = document

    # links
    def _l(self, name, uri, templated=False, quote=False, unquote=False):

        if(quote):
            uri = parse.quote(uri)
        if(unquote):
            uri = parse.unquote(uri)

        link = {'href':uri}
        if templated:
            link['templated'] = templated
        links = self.document.setdefault('_links', {})
        links[name] = link
        return self

    # curies (Compact URIs)
    def _c(self, name, uri, templated=True):
        curie = {
            'name': name,
            'href': uri,
        }
        if templated:
            curie['templated'] = True
        curies = self.document.setdefault('_links', {}).setdefault('curies', [])
        curies.append(curie)
        return self

    def _k(self, k, v):
        self.document[k] = v
        return self

    def _embed(self, key, resource):
        self.document.setdefault('_embedded', {})[key] = resource
        return self

if __name__=='__main__':
    r = Resource()
