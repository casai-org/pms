# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

DEV_URL = "https://api.sandbox.guesty.com/api/v2"
PROD_URL = "https://api.guesty.com/api/v2"


class API(object):
    api_key = None
    api_secret = None
    api_url = None

    def __init__(self, api_key=None, api_secret=None, sandbox=False):
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_url = DEV_URL if sandbox else PROD_URL

    def get(self, model_class):
        model = model_class(self)
        return model
