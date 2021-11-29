# Copyright (c) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class PMSReservationGuest(models.Model):
    _name = "pms.reservation.guest"
    _description = "PMS Reservation guest"

    name = fields.Char(string="Name", required=True)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    reservation_id = fields.Many2one("pms.reservation", string="Reservation")
    order_line_id = fields.Many2one("sale.order.line", string="Sale Order")
