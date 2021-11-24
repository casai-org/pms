# Copyright 2019  Pablo Quesada
# Copyright 2019  Dario Lodeiros
# Copyright (c) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ContractLine(models.Model):
    _inherit = "contract.line"

    property_id = fields.Many2one(
        "pms.property",
        string="Property",
    )

    def _prepare_invoice_line(self, move_form):
        res = super()._prepare_invoice_line(move_form=move_form)
        return res.update({"property_id": self.property_id.id})
