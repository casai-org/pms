# -*- coding: utf-8 -*-
import datetime
import logging

from odoo import models, fields, api
from odoo.exceptions import UserError
import requests

_log = logging.getLogger(__name__)


class BackendGuesty(models.Model):
    _name = "backend.guesty"

    name = fields.Char(required=True)
    api_key = fields.Char(required=True)
    api_secret = fields.Char(required=True)
    api_url = fields.Char(required=True)

    cleaning_product_id = fields.Many2one("product.product")

    def guesty_search_customer(self, guesty_id):
        guesty_partner = self.env["res.partner.guesty"].search([("guesty_id", "=", guesty_id)], limit=1)
        if not guesty_partner:
            # get data from guesty
            success, res = self.call_get_request(
                url_path="guests/{}".format(guesty_id)
            )

            if not success:
                raise UserError("Failed to get customer data from guesty")

            customer_name = res.get("fullName")
            if not customer_name:
                customer_name = "{} {}".format(
                    res.get("firstName"),
                    res.get("lastName")
                )

            body_payload = {
                "name": customer_name,
                "email": res.get("email"),
                "phone": res.get("phone")
            }

            base_partner = self.env["res.partner"].create(body_payload)

            customer = self.env["res.partner.guesty"].create({
                "partner_id": base_partner.id,
                "guesty_id": guesty_id
            })

            return customer
        else:
            return guesty_partner

    def check_credentials(self):
        # url to validate the credentials
        # this endpoint will search a list of users, it may be empty if the api key does not have permissions
        # to list the users, but it should be a 200 response
        # Note: Guesty does not provide a way to validate credentials
        success, result = self.call_get_request("search", limit=1)
        if success:
            raise UserError("Connection Test Succeeded! Everything seems properly set up!")
        else:
            raise UserError("Connection Test Failed!")

    def download_reservations(self):
        data = []
        skip = 0
        while True:
            success, res = self.call_get_request(
                url_path="reservations",
                skip=skip,
                params={
                    "fields": " ".join(["status", "checkIn", "checkOut", "listingId", "guestId"])
                }
            )

            if not success:
                break

            records = res.get("results", [])
            count = len(records)

            if count == 0:
                break
            else:
                skip += count

            data += records

        for record in data:
            guesty_id = record.get("_id")
            listing_id = record.get("listingId")
            check_in = record.get("checkIn")
            check_out = record.get("checkOut")
            status = record.get("status")
            guest_id = record.get("guestId")

            reservation_exists = self.env["pms.reservation"].search([
                ("guesty_id", "=", guesty_id)
            ], limit=1)

            pms_property = self.env["pms.property"].search([
                ("guesty_id", "=", listing_id)
            ], limit=1)

            pms_guest = self.guesty_search_customer(guest_id)
            check_in_time = datetime.datetime.strptime(check_in[0:19], "%Y-%m-%dT%H:%M:%S")
            check_out_time = datetime.datetime.strptime(check_out[0:19], "%Y-%m-%dT%H:%M:%S")

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

            if not reservation_exists and pms_property:
                self.env["pms.reservation"].with_context({
                    "ignore_overlap": True
                }).create({
                    "guesty_id": guesty_id,
                    "property_id": pms_property.id,
                    "start": check_in_time,
                    "stop": check_out_time,
                    "stage_id": stage_id.id,
                    "partner_id": pms_guest.partner_id.id
                })

    def call_get_request(self, url_path, params=None, skip=0, limit=25, success_codes=None):
        if success_codes is None:
            success_codes = [200, 201]

        if params is None:
            params = {}

        params.update({"skip": str(skip), "limit": str(limit)})

        url = "{}/{}".format(self.api_url, url_path)
        result = requests.get(
            url=url,
            params=params,
            auth=(self.api_key, self.api_secret)
        )

        if result.status_code in success_codes:
            return True, result.json()

        _log.error(result.content)
        return False, None

    def call_post_request(self, url_path, body):
        url = "{}/{}".format(self.api_url, url_path)
        result = requests.post(
            url=url,
            json=body,
            auth=(self.api_key, self.api_secret)
        )

        if result.status_code == 200:
            return True, result.json()
        else:
            return False, None

    def call_put_request(self, url_path, body):
        url = "{}/{}".format(self.api_url, url_path)
        result = requests.put(
            url=url,
            json=body,
            auth=(self.api_key, self.api_secret)
        )

        if result.status_code == 200:
            return True, result.json()
        else:
            return False, None
