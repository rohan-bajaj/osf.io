# -*- coding: utf-8 -*-

import json

from tornado.web import HTTPError


class WaterButlerError(HTTPError):
    def __init__(self, message, code=500, log_message=None):
        if isinstance(message, dict):
            self.data = message
            message = json.dumps(message)
        else:
            self.data = None
        super().__init__(code, log_message=log_message, reason=message)


class ProviderError(WaterButlerError):
    pass


class FileNotFoundError(ProviderError):
    def __init__(self, path):
        super().__init__(404, reason='Could not retrieve file or directory {0}'.format(message))
