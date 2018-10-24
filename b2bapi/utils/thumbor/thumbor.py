import libthumbor

class Thumbor:

    config = None
    THUMBOR_NATIVE_OPTIONS = ('crop', 'width', 'height', 'trim', 'smart',
                              'VALIGN', 'HALIGN', 'fit-in', 'orientation')

    def __init__(self, image_url, config=None):
        #self.image_url = self.url_encoded(image_url)
        self.image_url = image_url
        if config is None:
            config = self._default_config()
        self.config = config
        self.signer = libthumbor.CryptoURL(
            self.config['THUMBOR_SECURITY_KEY'])

    def _default_config(self):
        return dict(
            THUMBOR_SECURITY_KEY='MY_SECURE_KEY',
            THUMBOR_SERVER='http://localhost',
        )

    def prepend_host(self, url):
        return '/'.join([self.config['THUMBOR_SERVER'].rstrip('/'),
                         url.lstrip('/')])

    def signed_url(self, host=False):
        url = self.signer.generate(image_url=self.image_url, **self.options)
        return self.prepend_host(url) if host else url

    def unsafe_url(self, host=False):
        url = self.signer.generate(image_url=self.image_url, unsafe=True, 
                                    **self.options)
        return self.prepend_host(url) if host else url

    @property
    def options(self):
        try:
            rv = self._options
        except AttributeError:
            rv = self._options = {}
        return rv

    def reset_options(self):
        self._options = {}

    def crop(self, x1, y1, x2, y2):
        if None not in (x1, y1, x2, y2):
            self.options['crop'] = ((x1,y1),(x2,y2))
        return self

    def resize(self, width=None, height=None):
        if width or height:
            self.options['width'] = width or 0
            self.options['height'] = height or 0
        return self

    # TODO include trim and filters
    #def trim(self, enable=True):
    #    self.options['trim'] = enable or 0
    #    # 'trim:{trim}'.format(trim=trim)
    #    return self

    #def filters(self, options):
    #    filters = []
    #    for k,v in options.items():
    #        if k not in self.THUMBOR_NATIVE_OPTIONS:
    #            f = '{k}({v})'.format(k=k, v=v)
    #            filters.append(f)
    #    rv = 'filters:{filters}'.format(
    #            filters=':'.join(filters)) if filters else ''
    #    return rv
