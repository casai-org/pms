# Copyright (c) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import werkzeug.urls

from odoo import fields, models

from odoo.addons.http_routing.models.ir_http import slug


class PmsProperty(models.Model):
    _name = "pms.property"
    _inherit = ["pms.property", "website.published.mixin", "website.multi.mixin"]

    def _compute_website_url(self):
        for property in self:
            if property.id:
                property.website_url = "/property/%s" % slug(property)

    def google_map_link(self):
        property_partner = self.sudo().partner_id
        property_partner.geo_localize()
        params = {
            "q": "%s, %s"
            % (property_partner.partner_latitude, property_partner.partner_longitude),
            "z": 10,
        }
        return "https://maps.google.com/maps?" + werkzeug.urls.url_encode(params)

    property_category_id = fields.Many2one(
        string="Category", comodel_name="pms.website.category"
    )
