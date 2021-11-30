# Copyright (c) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models

from odoo.addons.http_routing.models.ir_http import slug


class PmsProperty(models.Model):
    _name = "pms.property"
    _inherit = ["pms.property", "website.published.mixin", "website.multi.mixin"]

    def _compute_website_url(self):
        for property in self:
            if property.id:
                property.website_url = "/property/%s" % slug(property)
