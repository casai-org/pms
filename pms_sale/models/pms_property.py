# Copyright (c) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class PmsProperty(models.Model):
    _inherit = "pms.property"

    checkin = fields.Float(string="Checkin")
    checkout = fields.Float(string="Checkout")
    reservation_ids = fields.One2many(
        "pms.property.reservation", "property_id", string="Reservation Types"
    )
    pms_mail_ids = fields.One2many("pms.mail", "property_id", string="Communication")
    no_of_guests = fields.Integer("Number of Guests")
    min_nights = fields.Integer("Minimum Nights")
    max_nights = fields.Integer("Maximum Nights")
    listing_type = fields.Selection(
        string="Listing Type",
        selection=[
            ("private_room", "Private Room"),
            ("entire_home", "Entire home"),
            ("shared_room", "Shared room"),
        ],
    )
