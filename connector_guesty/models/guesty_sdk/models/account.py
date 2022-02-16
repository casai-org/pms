# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from ..models import Model


class Account(Model):
    _name = "accounts"
    _fields = ["name"]

    def get_account_info(self):
        return self.search_by_id("me")
