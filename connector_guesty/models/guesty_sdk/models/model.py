# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import json
import logging

import requests

from ..fields import Field

_log = logging.getLogger(__name__)


class Model(object):
    _api = None
    _name = None
    _filters = []

    _default_fields = {"_id": Field("_id")}
    _fields = {}
    _all_fields = {}

    _skip = 0
    _limit = 100
    _count = 0
    _request_count = 0

    def __init__(self, api):
        self._api = api
        self._all_fields = self._default_fields.copy()
        self._all_fields.update(self._fields)

        if not self._name:
            self._name = self.__class__.__name__.lower()

    def create(self, payload=None, post_url=None):
        super().create()
        if not payload:
            return None

        _post_url = post_url or "{}/{}".format(self._api.api_url, self._name)
        result = requests.post(
            url=_post_url, json=payload, auth=(self._api.api_key, self._api.api_secret)
        )

        if result.status_code not in [200, 201]:
            return False, result.content

        return True, result.json()

    def delete(self, uuid=None, post_url=None):
        if not uuid:
            return False

        _post_url = post_url or "{}/{}/{}".format(self._api.api_url, self._name, uuid)
        result = requests.delete(
            url=_post_url, auth=(self._api.api_key, self._api.api_secret)
        )
        _log.info("API: {}".format(result.status_code))
        if result.status_code not in [204]:
            return False, result.content

        return True, None

    def with_filter(self, domain):
        if not domain:
            domain = []

        self._filters = [
            {"field": _d[0], "operator": _d[1], "value": _d[2]} for _d in domain
        ]

        return self

    def search(self):
        _get_url = "{}/{}".format(self._api.api_url, self._name)
        params = {}
        if self._filters:
            params["filters"] = json.dumps(self._filters)

        if self._fields:
            _fields = [
                self._all_fields[f].field_get_name()
                for f in self._all_fields
                if isinstance(self._all_fields[f], Field)
            ]

            params["fields"] = " ".join(_fields)

        _skip = self._skip
        _data = []
        while True:
            # print("Skip: {}".format(_skip))
            params.update({"skip": _skip, "limit": self._limit})
            # print(params)
            req = requests.get(
                url=_get_url,
                auth=(self._api.api_key, self._api.api_secret),
                params=params,
            )

            success, result = self._parse_request_result(req)
            # print(len(result))
            if success:
                _data += result
                _skip += len(result)
                if len(result) == 0:
                    break
            else:
                break

        return _data

    def search_by_id(self, uuid):
        _get_url = "{}/{}/{}".format(self._api.api_url, self._name, uuid)
        req = requests.get(url=_get_url, auth=(self._api.api_key, self._api.api_secret))
        success, res = self._parse_request_result(req)
        result = None
        if success and isinstance(res, list):
            if len(res) > 0:
                result = res[0]
            else:
                result = None
        elif success:
            result = res

        return success, result

    def _parse_request_result(self, req):
        _success = req.status_code == 200
        _data = []
        _result = []

        if _success:
            _result = req.json()
            if "count" in _result:
                self._request_count = _result["count"]

            if "results" in _result:
                _result = _result.get("results")
            else:
                _result = [_result]

        for _record in _result:
            rec = {}
            for _field in self._all_fields:
                _field_obj = self._all_fields[_field]
                rec[_field] = _field_obj.parse_value(_record)

            _data.append(rec)
            self._count += 1

        _log.info(
            "Parsing {}/{}/{} Records".format(
                len(_data), self._count, self._request_count
            )
        )
        return _success, _data
