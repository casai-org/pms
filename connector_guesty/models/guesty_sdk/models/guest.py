# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests

from ..fields import Field
from ..models import Model


class Guest(Model):
    _name = "guests"

    _fields = {
        "firstName": Field("firstName"),
        "hometown": Field("hometown"),
        "fullName": Field("fullName"),
    }

    def search_by_email(self, email):
        _get_url = "{}/{}".format(self._api.api_url, self._name)
        params = {"q": email}

        req = requests.get(
            url=_get_url,
            auth=(self._api.api_key, self._api.api_secret),
            params=params,
        )

        success, result = self._parse_request_result(req)
        return success, result
