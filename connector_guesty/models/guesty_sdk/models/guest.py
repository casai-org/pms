# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from ..fields import Field
from ..models import Model


class Guest(Model):
    _name = "guests"

    _fields = {"firstName": Field("firstName"), "hometown": Field("hometown")}
