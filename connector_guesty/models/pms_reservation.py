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
        self.guesty_search_customer()

    def guesty_push_reservation(self):
        backend = self.env.company.guesty_backend_id
        customer = backend.guesty_search_create_customer(self.partner_id)

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
                    "currency": self.sale_order_id.currency_id.name
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
            # retrieve calendars
            success, calendars = backend.call_get_request(
                url_path="listings/{}/calendar".format(self.property_id.guesty_id),
                params={
                    "from": self.start.strftime("%Y-%m-%d"),
                    "to": self.stop.strftime("%Y-%m-%d")
                }
            )

            if success:
                for calendar in calendars:
                    if calendar.get("status") == "unavailable":
                        raise ValidationError("Date {}, are not available to be blocked".format(calendar.get("date")))

                # todo: build a context title with the next format
                # block title examples
                # OPS-MNT-WKB AC Repair - Bedroom
                # DEV - PRE - EVC  No live
                # OPS - ROM - UNV exit unit
                block_title = "Blocked By: {}".format(self.partner_id.name)
                success, response = backend.call_put_request(
                    url_path="listings/calendars",
                    body={
                        "listings": [self.property_id.guesty_id],
                        "from": self.start.strftime("%Y-%m-%d"),
                        "to": self.stop.strftime("%Y-%m-%d"),
                        "status": "unavailable",
                        "note": block_title
                    }
                )

                _log.info(success)
                _log.info(response)

    def guesty_pull_reservation(self, backend, payload):
        _id, reservation = self.sudo().guesty_parse_reservation(payload, backend)
        reservation_id = self.sudo().search([
            ("guesty_id", "=", _id)
        ], limit=1)

        if not reservation_id:
            reservation_id = self.env["pms.reservation"].sudo().with_context({
                "ignore_overlap": True
            }).create(reservation)

            invoice_lines = payload.get("money", {}).get("invoiceItems")
            no_nights = payload.get("nightsCount", 0)

            reservation_id.build_so(invoice_lines, no_nights, backend)
        else:
            reservation_id.sudo().with_context({
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
        pms_guest = backend.sudo().guesty_search_pull_customer(guest_id)

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

    def build_so(self, guesty_invoice_items, no_nights, backend):
        # Create SO based on reservation
        # When the reservation was created out of odoo
        if guesty_invoice_items is None:
            raise ValidationError("Unable to create SO without guesty data")

        if not backend:
            raise ValidationError("No Backend defined")

        if self.sale_order_id:
            return self.sale_order_id

        order_lines = []
        for line in guesty_invoice_items:
            if line.get("type") == "ACCOMMODATION_FARE":
                reservation_type = self.property_id.reservation_ids.filtered(
                    lambda s: s.is_guesty_price)

                if not reservation_type:
                    raise ValidationError("Missing guesty reservation type")

                order_lines.append({
                    "product_id": reservation_type.product_id.id,
                    "name": reservation_type.display_name,
                    "product_uom_qty": no_nights,
                    "price_unit": line.get("amount"),
                    "property_id": self.property_id.id,
                    "reservation_id": reservation_type.id,
                    "pms_reservation_id": self.id,
                    "start": self.start,
                    "stop": self.stop,
                    "no_of_guests": 1  # Todo: Set correct number of guests
                })
            elif line.get("type") == "CLEANING_FEE":
                order_lines.append({
                    "product_id": backend.sudo().cleaning_product_id.id,
                    "name": backend.sudo().cleaning_product_id.name,
                    "product_uom_qty": 1,
                    "price_unit": line.get("amount")
                })

        so = self.env["sale.order"].sudo().create({
            "partner_id": self.partner_id.id,
            "order_line": [(0, False, line) for line in order_lines]
        })

        self.sudo().write({
            "sale_order_id": so.id
        })
