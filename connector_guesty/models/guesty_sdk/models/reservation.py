# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from ..fields import Field
from ..models import Model


class Reservation(Model):
    _name = "reservations"

    _fields = {
        "listingId": Field("listingId"),
        "guestId": Field("guestId"),
        "checkIn": Field("checkIn"),
        "checkOut": Field("checkOut"),
        "createdAt": Field("createdAt"),
        "lastUpdatedAt": Field("lastUpdatedAt"),
        "closedAt": Field("closedAt"),
        "confirmedAt": Field("confirmedAt"),
        "keyCode": Field("keyCode"),
        "status": Field("status"),
        "money": Field("money"),
        "listing": Field("listing"),
        "nightsCount": Field("nightsCount"),
    }


#  "status",
# "checkIn",
# "checkOut",
# "listingId",
# "guestId",
# "listing.nickname",
# "lastUpdatedAt",
# "money",
# "nightsCount",
