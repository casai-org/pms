# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import fields, models

_log = logging.getLogger(__name__)


class SaleOrderMultiWizard(models.Model):
    _name = "sale.order.multi.wizard"

    crm_lead_id = fields.Many2one("crm.lead")
    line_ids = fields.Many2many("pms.available.listing")
