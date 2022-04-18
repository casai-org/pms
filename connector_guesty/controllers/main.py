# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

_log = logging.getLogger(__name__)


def standardize_request_data(data):
    """
    Standardize the request data to be able to use it in the controller.
    """
    standard_data = {}
    if data.get("reservation") and data.get("event"):
        if data.get("event") in ["reservation.new", "reservation.updated"]:
            standard_data["reservation"] = data.get("reservation")
            standard_data["event"] = data.get("event")
        elif data.get("event") and data.get("event", {}).get("reservation"):
            standard_data["reservation"] = data.get("event").get("reservation")
            standard_data["event"] = "reservation.updated"

    return standard_data["reservation"], standard_data["event"]


class GuestyController(http.Controller):
    def validate_get_company(self, payload):
        company_id = payload.get("company")
        if not company_id:
            raise ValidationError(_("No company was specified"))
        company = request.env["res.company"].browse(company_id)
        if not company:
            raise ValidationError(_("Invalid company"))
        backend = company.guesty_backend_id
        if not backend:
            raise ValidationError(_("No backend was defined"))
        return company, backend

    @http.route(
        "/guesty/reservations_webhook",
        methods=["POST"],
        auth="public",
        csrf=False,
        type="json",
    )
    def reservations_webhook(self, **data):
        reservation_info, event_name = standardize_request_data(request.jsonrequest)
        if event_name not in ["reservation.new", "reservation.updated"]:
            raise ValidationError(_("Invalid event name {}".format(event_name)))

        guesty_listing_id = reservation_info.get("listingId")
        listing_obj = (
            request.env["pms.guesty.listing"]
            .sudo()
            .search([("external_id", "=", guesty_listing_id)], limit=1)
        )
        _log.info(listing_obj)

        if not listing_obj.exists():
            raise ValidationError(_("Listing not found {}".format(guesty_listing_id)))

        request.env["pms.reservation"].with_delay().guesty_pull_reservation(
            reservation_info, event_name
        )
        return {"success": True}

    def _resevations_webhook(self, **data):
        if data.get("event") and data.get("event").get("reservation"):
            version = "1.0"
        else:
            version = "2.0"

        if version == "1.0":
            reservation = data.get("event").get("reservation")
        else:
            reservation = request.jsonrequest.get("reservation")

        if not reservation:
            raise ValidationError(_("Reservation data not found!"))

        property_id = (
            request.env["pms.property"]
            .sudo()
            .search([("guesty_id", "=", reservation.get("_id"))])
        )
        company_id = property_id.company_id

        if not company_id:
            raise ValidationError(_("No company was found"))

        backend = company_id.guesty_backend_id
        if not backend:
            raise ValidationError(_("No backend was found"))

        success, res = backend.sudo().call_get_request(
            url_path="reservations/{}".format(reservation.get("_id")),
            params={
                "fields": " ".join(
                    [
                        "status",
                        "checkIn",
                        "checkOut",
                        "listingId",
                        "guestId",
                        "listing.nickname",
                        "lastUpdatedAt",
                        "money",
                        "nightsCount",
                        "plannedArrival",
                        "plannedDeparture",
                    ]
                )
            },
        )

        if success:
            request.env["pms.reservation"].with_company(
                company_id
            ).with_delay().guesty_pull_reservation(backend, res)
            return {"success": True}
        else:
            raise ValidationError(str(res))

    @http.route(
        "/guesty/listing_webhook",
        methods=["POST"],
        auth="public",
        csrf=False,
        type="json",
    )
    def listing_webhook(self, **data):
        company, backend = self.validate_get_company(data)
        event = data.get("event")
        listing = event.get("listing")
        if not listing:
            raise ValidationError(_("Listing data not found"))
        request.env["pms.property"].with_delay().guesty_pull_listing(backend, listing)
        return {"success": True}

    @http.route(
        "/guesty/webhook", methods=["POST"], auth="public", csrf=False, type="json"
    )
    def webhook(self):
        data = request.jsonrequest
        if data.get("event") == "listing.calendar.updated":
            # do actions for calendars
            self.do_calendar_update(data)

    def do_calendar_update(self, payload):
        calendar_dates = payload.get("calendar", [])
        for calendar in calendar_dates:
            request.env[
                "pms.guesty.calendar"
            ].sudo().with_delay().guesty_pull_calendar_event(calendar)
