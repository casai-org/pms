# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import datetime


class Field(object):
    _field_name = None
    _default = None

    def __init__(self, field_name=None, default=None):
        super().__init__()
        self._field_name = field_name
        self._default = default

    def field_get_name(self):
        return self._field_name

    def parse_value(self, value):
        return value.get(self._field_name, self._default)


class JsonField(Field):
    def parse_value(self, value):
        _val = value
        for i in self._field_name.split("."):
            _val = _val.get(i)
        return _val


class DatetimeField(Field):
    def parse_value(self, value):
        _str = value.get(self._field_name, self._default)
        if _str:
            _date_str = _str[0:19]
            return datetime.datetime.strptime(_date_str, "%Y-%m-%dT%H:%M:%S")

        return _str
