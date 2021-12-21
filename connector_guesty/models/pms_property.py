# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
import random
import string

_log = logging.getLogger(__name__)


class PmsProperty(models.Model):
    _inherit = "pms.property"

    guesty_id = fields.Char()

    def action_guesty_push_property(self):
        self.with_delay().guesty_push_property()

    def guesty_push_property(self):
        code = ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=6))  # todo: Remove and use the property name
        backend = self.env["backend.guesty"].search([], limit=1)  # identify what is the correct record

        # Guesty use a specific format for address, and autofill the other address fields
        address = "{}, {}, {}, {}, {}, {}".format(
            self.street,
            self.street2,
            self.city,
            self.zip,
            self.state_id.code,
            self.state_id.name
        )

        body = {
            "title": "Test Property",
            "nickname": code,
            "address": {
                "full": address
            },
            "prices": {
                "currency": "USD",
                "basePrice": 30,
                "cleaningFee": 17
            },
            "financials": {
                "cleaningFee": {
                    "value": {
                        "formula": 17,
                        "multiplier": "PER_STAY",
                        "valueType": "FIXED"
                    }
                }
            }
        }

        if len(self.reservation_ids):
            # we are taking the first record, but we need to have and identifier
            reservation_type = self.reservation_ids[0]
            body["prices"]["basePrice"] = reservation_type.price

        if self.guesty_id:
            success, result = backend.call_put_request(
                url_path="listings/{}".format(self.guesty_id),
                body=body
            )
        else:
            success, result = backend.call_post_request(
                url_path="listings",
                body=body
            )

        if success and not self.guesty_id:
            guesty_id = result.get("id")
            self.write({
                "guesty_id": guesty_id
            })

    def guesty_pull_listing(self, backend, payload):
        _id, property_data = self.sudo().guesty_parse_listing(payload, backend)
        property_id = self.sudo().search([
            ("guesty_id", "=", _id)
        ], limit=1)

        if not property_id:
            self.env["pms.property"].sudo().create(property_data)
        else:
            property_id.write(property_data)

        return True

    def map_listing_type(self, guesty_type):
        if guesty_type == "SINGLE":
            return "private_room"

    def guesty_parse_listing(self, payload, backend):
        guesty_id = payload.get("id")
        property_data = {
            "guesty_id": guesty_id,
            "name": payload.get("nickname"),
            "listing_type": payload.get("type"),
            "owner_id": 1  # todo: Change and define a default owner
        }
        listing_type = payload.get("type")
        listing_type_mapped = self.map_listing_type(listing_type)
        if listing_type and listing_type_mapped:
            property_data["listing_type"] = listing_type_mapped

        guesty_address = payload.get("address", {})

        street = guesty_address.get("street")
        if street:
            property_data["street"] = street
        city = guesty_address.get("city")
        if city:
            property_data["city"] = city
        zip_code = guesty_address.get("zipcode")
        if zip_code:
            property_data["zip"] = zip_code
        country = guesty_address.get("country")
        if country:
            if country.lower() in ["mexico", "méxico"]:
                res_country = self.env.ref("base.mx", raise_if_not_found=False)
            else:
                res_country = self.env["res.country"].search([
                    ("name", "=", country)
                ], limit=1)

            if res_country:
                property_data["country_id"] = res_country.id

        listing_timezone = payload.get("timezone")
        if listing_timezone:
            property_data["tz"] = listing_timezone

        return guesty_id, property_data
