# -*- coding: utf-8 -*-
import logging
import datetime

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

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

    def guesty_pull_reservation(self, backend, payload):
        _id, reservation = self.sudo().guesty_parse_reservation(payload, backend)
        reservation_id = self.search([
            ("guesty_id", "=", _id)
        ], limit=1)

        if not reservation_id:
            self.env["pms.reservation"].with_context({
                "ignore_overlap": True
            }).create(reservation)
        else:
            self.env["pms.reservation"].with_context({
                "ignore_overlap": True
            }).write(reservation)

        return True

    def guesty_map_reservation_status(self, status):
        if status == "inquiry":
            stage_id = self.env.ref("pms_sale.pms_stage_new", raise_if_not_found=False)
        elif status == "reserved":
            stage_id = self.env.ref("pms_sale.pms_stage_booked", raise_if_not_found=False)
        elif status == "confirmed":
            stage_id = self.env.ref("pms_sale.pms_stage_confirmed", raise_if_not_found=False)
        elif status in ["canceled", "declined", "expired", "closed"]:
            stage_id = self.env.ref("pms_sale.pms_stage_cancelled", raise_if_not_found=False)
        else:
            stage_id = self.env.ref("pms_sale.pms_stage_new", raise_if_not_found=False)

        return stage_id

    def guesty_parse_reservation(self, reservation, backend):
        guesty_id = reservation.get("_id")
        listing_id = reservation.get("listingId")
        check_in = reservation.get("checkIn")
        check_out = reservation.get("checkOut")
        status = reservation.get("status")
        guest_id = reservation.get("guestId")

        property_id = self.env["pms.property"].search([
            ("guesty_id", "=", listing_id)
        ], limit=1)

        if not property_id.exists():
            raise ValidationError("Listing: {} does not exist".format(listing_id))

        stage_id = self.guesty_map_reservation_status(status)
        pms_guest = backend.sudo().guesty_search_customer(guest_id)

        check_in_time = datetime.datetime.strptime(check_in[0:19], "%Y-%m-%dT%H:%M:%S")
        check_out_time = datetime.datetime.strptime(check_out[0:19], "%Y-%m-%dT%H:%M:%S")

        return guesty_id, {
            "guesty_id": guesty_id,
            "property_id": property_id.id,
            "start": check_in_time,
            "stop": check_out_time,
            "stage_id": stage_id.id,
            "partner_id": pms_guest.partner_id.id
        }
