# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerGuesty(models.Model):
    _name = "res.partner.guesty"
    _description = "Guesty Partner"

    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    guesty_id = fields.Char(required=True)
    guesty_account_id = fields.Char()
    guesty_name = fields.Char()
    is_guesty_default = fields.Boolean()

    def guesty_get_backend_single(self):
        _backend_list = self.env["backend.guesty"].search(
            [
                ("guesty_account_id", "in", self.mapped("guesty_account_id")),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        return _backend_list

    @api.constrains("guesty_id")
    def check_unique_guesty_id(self):
        exists = self.search(
            [("guesty_id", "=", self.guesty_id), ("id", "!=", self.id)], limit=1
        )

        if exists:
            raise ValidationError(
                _("Guest already exists on guesty as: ({}, {}, {})").format(
                    exists.id, exists.partner_id.name, exists.guesty_id
                )
            )
