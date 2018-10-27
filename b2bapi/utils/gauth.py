import functools
import urllib
import os
import hashlib
import requests
from flask import current_app as app

# for token verification
from google.oauth2 import id_token
from google.auth.transport import requests as gauth_requests

class GAuth:
    default_providers = ('google', 'microsoft', 'linkedin', 'facebook')
    CONFIG = {
        'client_id' : ('599748317391-pbhmepmam968t0ppfm43afs12i2jotlq.'
                        'apps.googleusercontent.com'),
        'secret': 'FZ9_obFHhGNijCx0rqLt2P4S',
        'auth_uri' : 'https://accounts.google.com/o/oauth2/v2/auth',
        'redirect_uri': 'http://localhost:8080',
        'params_template' : {
            'client_id' : None,
            'response_type' : 'code',
            'scope' : 'openid email',
            'nonce' : '',
            #'login_hint' : '',
        },
        'discovery': {
            'uri': ('https://accounts.google.com/.well-known'
                    '/openid-configuration'),
            'document': None,
        }
    }

    @property
    def document():
        if not self.CONFIG['discovery']['document']:
            self._load_discovery()
        return self.CONFIG['discovery']['document']

    def _load_discovery(self):
        response = requests.get(self.CONFIG['discovery']['uri'])
        self.CONFIG['discovery']['document'] = response.json()

    """
    In case you receive the token from the user.
    """
    def verify_token(self, token):
        # as seen in: https://developers.google.com/identity/sign-in/web/backend-auth#verify-the-integrity-of-the-id-token
        issuers = ['accounts.google.com', 'https://accounts.google.com']
        try:
            # Specify the CLIENT_ID of the app that accesses the backend:
            idinfo = id_token.verify_oauth2_token(
                token, gauth_requests.Request(), self.CONFIG['client_id'])


            if idinfo['iss'] not in issuers:
                raise ValueError('Wrong issuer.')
            return idinfo
        except ValueError:
            # Invalid token
            pass

    def get_access_token(self, code):
        config = self.CONFIG
        token_endpoint = self.document['token_endpoint']
        return requests.post(token_endpoint, data={
            'code': code,
            'client_id': config['client_id'], 
            'client_secret': config['secret'],
            'redirect_uri': config['redirect_uri'], 
            'grant_type': 'authorization_code',
            # 'access_type': 'offline', # to include refresh_token in response
        }).json()

    def generate_uri(self, base_uri, params=None):
        params_str = "&".join(["{}={}".format(k,urllib.parse.quote(v, safe=''))
                               for k,v in params.items() if v is not None])
        return "?".join([base_uri, params_str])

    def get_google_openid_params(self, **kw):
        config = self.CONFIG
        params = config['params_template'].copy()
        params['client_id'] = config['client_id']
        if not kw:
            return params
        for k,v in kw.items():
            params[k] = v
        return params

    def get_google_openid_uri(self, **kw):
        base_uri = config['auth_uri']
        params = self.get_google_openid_params(**kw)
        return self.generate_uri(base_uri, params)
