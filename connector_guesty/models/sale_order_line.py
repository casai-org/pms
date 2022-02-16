# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import fields, models

_log = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    guesty_is_locked = fields.Boolean(default=False)
    guesty_type = fields.Char()
    guesty_normal_type = fields.Char()
    guesty_second_identifier = fields.Char()

    def write(self, values):
        return super().write(values)

    def _get_display_price(self, product):
        if (
            self.company_id.guesty_backend_id
            and self.reservation_ok
            and self.start
            and self.stop
        ):
            # todo: Fix Calendar
            success, result = self.sudo().company_id.guesty_backend_id.call_get_request(
                url_path="availability-pricing/api/calendar/listings/{}".format(
                    self.sudo().property_id.guesty_id
                ),
                paginate=False,
                params={
                    "startDate": self.start.strftime("%Y-%m-%d"),
                    "endDate": self.stop.strftime("%Y-%m-%d"),
                },
            )

            # todo: Fix Calendar
            if success:
                calendar_data = result.get("data", {}).get("days", [])
                prices = [calendar.get("price") for calendar in calendar_data]
                avg_price = sum(prices) / len(prices)

                currency_name = calendar_data[0]["currency"]
                currency_id = (
                    self.env["res.currency"]
                    .sudo()
                    .search([("name", "=", currency_name)], limit=1)
                )

                if not currency_id:
                    currency_id = self.sudo().env.ref(
                        "base.USD", raise_if_not_found=False
                    )

                # noinspection PyProtectedMember
                price_currency = currency_id._convert(
                    avg_price,
                    self.currency_id,
                    self.order_id.company_id,
                    self.order_id.date_order,
                )
                return price_currency
        # noinspection PyProtectedMember
        return super()._get_display_price(product)
