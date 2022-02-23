# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import fields, models

_log = logging.getLogger(__name__)


class PmsAvailableListing(models.Model):
    _name = "pms.available.listing"

    lead_id = fields.Many2one("crm.lead")
    property_id = fields.Many2one("pms.property", required=1)
    currency = fields.Char()
    price = fields.Float()
    have_quotation = fields.Boolean()

    def do_quote(self):
        self.sudo().have_quotation = True
