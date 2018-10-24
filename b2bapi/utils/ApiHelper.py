import requests
import json
import functools
from datetime import datetime
import dateutil.parser
import time
from flask import Markup, url_for, g, session as flask_session, redirect, abort
from ccaapi.config import default as default_config

class ApiHelper(object):

    base_url = None
    auth = None
    httpconn = None
    token = None
    default_headers = None

    def __init__(self):
        self.base_url = default_config.CACHE_API_PREFIX
        self.default_headers = {'content-type': 'application/json'}
        self.httpconn = requests.Session()
        self.httpconn.auth = (default_config.CACHE_API_USER, default_config.CACHE_API_PASS)

    def get(self, url, params=None, headers=None, pre_embed_targets=None):

        res = self.httpconn.get(
            self.base_url + self.prepare_url(url), 
            params=params,
            headers=headers or self.default_headers
        )
        
        if not self.is_response_error(res):
            data = res.json()
            res_obj = APIResource(data, self)
            if pre_embed_targets:
                res_obj.pre_embed(pre_embed_targets)
            return res, res_obj
        else:
            return res, None

    def prepare_url(self, raw_url):
        return raw_url

    def is_response_error(self, response):
        return not response or response.status_code >= 400

class APIResource(dict):
    def __init__(self, store, api_client):
        self.api_client = api_client
        self.store = store
        super(APIResource, self).__init__(store)
        self.pre_embed()

    def __getitem__(self, key, targets=None):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            if key == 'embed':
                url_key = 'url'
                try:
                    url = dict.__getitem__(self, url_key)
                    if url:
                        response, embed = self.api_client.get(url, pre_embed_targets=targets)
                        self[key] = embed
                        return dict.__getitem__(self, key)
                    else:
                        self[key] = None
                        return None
                except KeyError:
                    raise
            if key.endswith('_embed'):
                url_key = key.replace('_embed', '_url')
                try:
                    url = dict.__getitem__(self, url_key)
                    if url:
                        response, embed = self.api_client.get(url, pre_embed_targets=targets)
                        self[key] = embed
                        return dict.__getitem__(self, key)
                    else:
                        self[key] = None
                        return None
                except KeyError:
                    raise
            elif key.endswith('_embeds'):
                urls_key = key.replace('_embeds', '_urls')
                try:
                    urls = dict.__getitem__(self, urls_key)
                    if urls:
                        self[key] = []
                        for url in urls:
                            response, embed = self.api_client.get(url, pre_embed_targets=targets)
                            self[key].append(embed)
                        return dict.__getitem__(self, key)
                    else:
                        self[key] = None
                        return None
                except KeyError:
                    raise
            else:
                raise

    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)

    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)

    def pre_embed(self, targets=[]):
        # targets = targets + self.lazyloaded_targets
        self.pre_embed_try_keys(targets)
        for k, v in self.iteritems():
            self[k] = self.pre_embed_convert(k, v, targets)

    def pre_embed_convert(self, key, val, targets):
        if isinstance(val, dict):
            if not isinstance(val, APIResource):
                val = APIResource(val, self.api_client)
            val.pre_embed(targets)
        elif isinstance(val, list):
            for idx, v in enumerate(val):
                if isinstance(v, dict):
                    if not isinstance(val, APIResource):
                        val[idx] = APIResource(v, self.api_client)
                    val[idx].pre_embed(targets)
        return val

    def pre_embed_try_keys(self, targets):
        for key in targets:
            try:
                self.__getitem__(key, targets)
            except:
                # only preembedding here, skip Key errors
                pass