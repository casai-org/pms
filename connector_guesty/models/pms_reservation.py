# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_log = logging.getLogger(__name__)


class PmsReservation(models.Model):
    _inherit = "pms.reservation"

    guesty_id = fields.Char()

    @api.constrains("property_id", "stage_id", "start", "stop")
    def _check_no_of_reservations(self):
        if self.env.context.get('ignore_overlap'):
            return

        return super(PmsReservation, self)._check_no_of_reservations()

    def action_book(self):
        res = super(PmsReservation, self).action_book()
        if not res:
            raise UserError("Something went wrong")

        # Validate data
        if not self.property_id.guesty_id:
            raise ValidationError("Property not linked to guesty")

        # Send to guesty
        self.with_delay().guesty_push_reservation()

    def action_search_customer(self):
        backend = self.env.company.guesty_backend_id
        self.guesty_search_customer(backend)

    def guesty_search_customer(self, backend):
        guesty_partner = self.env["res.partner.guesty"].search([("partner_id", "=", self.partner_id.id)], limit=1)
        if not guesty_partner:
            # create on guesty
            body = {
                "fullName": self.partner_id.name,
                "email": self.partner_id.email,
                "phone": self.partner_id.phone
            }
            success, res = backend.call_post_request(
                url_path="guests",
                body=body
            )

            if not success:
                raise UserError("Unable to create customer")

            guesty_id = res.get("_id")
            customer = self.env["res.partner.guesty"].create({
                "partner_id": self.partner_id.id,
                "guesty_id": guesty_id
            })

            return customer
        else:
            return guesty_partner

    def guesty_push_reservation(self):
        backend = self.env.company.guesty_backend_id
        customer = self.guesty_search_customer(backend)

        body = {
            "listingId": self.property_id.guesty_id,
            "checkInDateLocalized": self.start.strftime("%Y-%m-%d"),
            "checkOutDateLocalized": self.stop.strftime("%Y-%m-%d"),
            "guestId": customer.guesty_id,
            "status": "inquiry"
        }

        if self.sale_order_id:
            # create a reservation on guesty
            reservation_line = self.sale_order_id.order_line.filtered(lambda s: s.reservation_ok)
            if reservation_line:
                body["money"] = {
                    "fareAccommodation": reservation_line.price_subtotal,
                }

            cleaning_line = self.sale_order_id.order_line.filtered(
                lambda s: s.product_id.id == backend.cleaning_product_id.id)

            if cleaning_line and reservation_line:
                body["money"]["fareCleaning"] = cleaning_line.price_subtotal

            success, res = backend.call_post_request(
                url_path="reservations",
                body=body
            )

            if not success:
                raise UserError("Unable to send to guesty")

            guesty_id = res.get("_id")
            self.guesty_id = guesty_id
        else:
            # block calendar
            raise UserError("Reservation without a SO are not implemented")
