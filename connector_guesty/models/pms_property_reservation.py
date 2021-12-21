# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PmsPropertyReservation(models.Model):
    _inherit = "pms.property.reservation"

    is_guesty_price = fields.Boolean()

    @api.constrains("property_id", "is_guesty_price")
    def _check_single_guesty_price(self):
        if self.is_guesty_price:
            check = self.search([
                ("property_id", "=", self.property_id.id),
                ("is_guesty_price", "=", True),
                ("id", "!=", self.id)
            ])

            if check:
                raise ValidationError("Multiple guesty prices are not allowed")
