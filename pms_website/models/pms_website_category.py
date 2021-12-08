# Copyright (c) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class PMSWebsiteCategory(models.Model):
    _name = "pms.website.category"

    name = fields.Char(string="Category Name", help="Category Name", required=True)
    parent_category_id = fields.Many2one(
        string="Parent Category", comodel_name="pms.website.category"
    )
