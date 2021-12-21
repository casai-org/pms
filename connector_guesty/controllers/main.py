# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_log = logging.getLogger(__name__)


class GuestyController(http.Controller):
    def validate_get_company(self, payload):
        company_id = payload.get("company")
        if not company_id:
            raise ValidationError("No company was specified")

        company = request.env["res.company"].browse(company_id)
        if not company:
            raise ValidationError("Invalid company")

        backend = company.guesty_backend_id
        if not backend:
            raise ValidationError("No backend was defined")

        return company, backend

    @http.route("/guesty/reservations_webhook", methods=['POST'], auth='public', csrf=False, type='json')
    def reservations_webhook(self, **data):
        company, backend = self.validate_get_company(data)
        event = data.get("event")
        reservation = event.get("reservation")
        if not reservation:
            raise ValidationError("Reservation data not found!")

        request.env["pms.reservation"].with_delay().guesty_pull_reservation(backend, reservation)
        return {
            "success": True
        }

    @http.route("/guesty/listing_webhook", methods=['POST'], auth='public', csrf=False, type='json')
    def listing_webhook(self, **data):
        company, backend = self.validate_get_company(data)
        event = data.get("event")
        listing = event.get("listing")
        if not listing:
            raise ValidationError("Listing data not found")

        request.env["pms.property"].with_delay().guesty_pull_listing(backend, listing)

        return {
            "success": True
        }
