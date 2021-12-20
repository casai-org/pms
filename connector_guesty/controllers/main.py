# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_log = logging.getLogger(__name__)


class GuestyController(http.Controller):

    @http.route("/guesty/reservations_webhook", methods=['POST'], auth='public', csrf=False, type='json')
    def reservations_webhook(self, **data):
        company_id = data.get("company")
        if not company_id:
            raise ValidationError("No company was specified")

        company = request.env["res.company"].browse(company_id)
        backend = company.guesty_backend_id
        if not backend:
            raise ValidationError("No backed was defined")

        event = data.get("event")
        reservation = event.get("reservation")
        if not reservation:
            raise ValidationError("Reservation data not found!")

        request.env["pms.reservation"].with_delay().guesty_pull_reservation(backend, reservation)
        return {
            "success": True
        }
