# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import api, fields, models

_log = logging.getLogger(__name__)


class PmsAvailableListing(models.Model):
    _name = "pms.available.listing"

    lead_id = fields.Many2one("crm.lead")
    property_id = fields.Many2one("pms.property", required=1)
    currency = fields.Char()
    price = fields.Float()
    have_quotation = fields.Boolean()
    no_nights = fields.Integer()
    check_in = fields.Date()
    check_out = fields.Date()
    amount_total = fields.Float(compute="_compute_total", store=False)

    currency_id = fields.Many2one("res.currency")
    city = fields.Char(related="property_id.city")
    tag_ids = fields.Many2many("pms.tag", related="property_id.tag_ids")

    def _compute_total(self):
        for _self in self:
            _self.amount_total = _self.no_nights * _self.price

    @api.model
    def create(self, vals_list):
        if "currency" in vals_list:
            vals_list["currency_id"] = (
                self.env["res.currency"]
                .search([("name", "=", vals_list["currency"])], limit=1)
                .id
            )

        return super(PmsAvailableListing, self).create(vals_list)

    def do_quote(self):
        self.sudo().have_quotation = True
