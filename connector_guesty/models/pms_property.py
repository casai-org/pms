# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
import random
import string

_log = logging.getLogger(__name__)


class PmsProperty(models.Model):
    _inherit = "pms.property"

    guesty_id = fields.Char()

    # guesty_title = fields.Char()
    # guesty_description = fields.Text()
    # guesty_summary = fields.Text()

    def action_guesty_push_property(self):
        self.with_delay().guesty_push_property()

    # @api.model
    # def create(self, values):
    #     result = super(PmsProperty, self).create(values)
    #     result.with_delay().guesty_push_property()
    #     return result

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
