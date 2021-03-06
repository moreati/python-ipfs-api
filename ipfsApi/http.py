"""
HTTP client for api requests.  This is pluggable into the IPFS Api client and
can/will eventually be supplemented with an asynchronous version.
"""
from __future__ import absolute_import

import requests
import contextlib

from . import encoding
from .exceptions import ipfsApiError


def pass_defaults(f):
    """
    Use instance default kwargs updated with those passed to function.
    """
    def wrapper(self, *args, **kwargs):
        merged = {}
        merged.update(self.defaults)
        merged.update(kwargs)
        return f(self, *args, **merged)
    return wrapper


class HTTPClient(object):

    def __init__(self, host, port, base, default_enc, **defaults):
        self.host = host
        self.port = port
        self.base = 'http://%s:%s/%s' % (host, port, base)

        # default request keyword-args
        if 'opts' in defaults:
            defaults['opts'].update({'encoding': default_enc})
        else:
            defaults.update({'opts': {'encoding': default_enc}})

        self.default_enc  = encoding.get_encoding(default_enc)
        self.defaults = defaults
        self._session = None

    @pass_defaults
    def request(self, path,
                args=[], files=[], opts={},
                decoder=None, **kwargs):

        url = self.base + path

        params = []
        params.append(('stream-channels', 'true'))

        for opt in opts.items():
            params.append(opt)
        for arg in args:
            params.append(('arg', arg))

        method = 'post' if (files or 'data' in kwargs) else 'get'

        if self._session:
            res = self._session.request(method, url,
                                        params=params, files=files, **kwargs)
        else:
            res = requests.request(method, url,
                                   params=params, files=files, **kwargs)

        if not decoder:
            try:
                ret = self.default_enc.parse(res.text)
            except:
                ret = res.text
        else:
            enc = encoding.get_encoding(decoder)
            try:
                ret = enc.parse(res.text)
            except:
                ret = res.text

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError:
            # If we have decoded an error response from the server,
            # use that as the exception message; otherwise, just pass
            # the exception on to the caller.
            if 'Message' in ret:
                raise ipfsApiError(ret['Message'])
            else:
                raise
        return ret

    @contextlib.contextmanager
    def session(self):
        self._session = requests.session()
        yield
        self._session.close()
        self._session = None
