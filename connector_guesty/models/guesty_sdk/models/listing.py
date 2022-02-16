# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from ..fields import Field
from ..models import Model


class Listing(Model):
    _name = "listings"

    _fields = {
        "nickname": Field("nickname"),
        "title": Field("title"),
        "roomType": Field("roomType"),
        "listing_type": Field("listing_type"),
        "address": Field("address"),
        "timezone": Field("timezone"),
        "defaultCheckInTime": Field("defaultCheckInTime"),
        "defaultCheckOutTime": Field("defaultCheckOutTime"),
        "accommodates": Field("accommodates"),
        "terms": Field("terms"),
        "pictures": Field("pictures"),
    }
