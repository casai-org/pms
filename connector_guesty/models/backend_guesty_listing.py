# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import _, fields, models

_log = logging.getLogger(__name__)


class BackendGuestyListing(models.Model):
    _name = "backend.guesty.listing"

    name = fields.Char()
    nickname = fields.Char()
    guesty_account = fields.Char()
    external_id = fields.Char()
    property_ids = fields.Many2many("pms.property")

    _sql_constraints = [
        (
            "external_id_uniq",
            "unique(external_id)",
            _("Listing external id must be unique!"),
        )
    ]
