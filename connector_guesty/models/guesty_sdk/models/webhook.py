# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from ..fields import Field
from ..models import Model


class Webhook(Model):
    _name = "webhooks"

    _fields = {
        "url": Field("url"),
        "accountId": Field("accountId"),
        "events": Field("events"),
    }

    def create(self, url=None, account_id=None, events=None, **kwargs):
        payload = {"url": url, "accountId": account_id, "events": events}

        return super().create(payload=payload, **kwargs)
