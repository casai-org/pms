# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import _, api, models
from odoo.exceptions import ValidationError

_log = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange("product_uom", "product_uom_qty")
    def product_uom_change(self):
        super().product_uom_change()
        if self.company_id.guesty_backend_id and self.reservation_id:
            # get calendar data from guesty
            if not self.property_id:
                raise ValidationError(_("No property defined on SO for reservation"))

            if not self.property_id.guesty_id:
                raise ValidationError(_("No listing defined on property"))

            if not self.start or not self.stop:
                raise ValidationError(_("Invalid dates on SO reservation"))

            # self.env["pms.guesty.calendar"].compute_price(
            #     self.property_id,
            #     self.start,
            #     self.stop,
            #     self.order_id.currency_id
            # )

            success, result = self.company_id.guesty_backend_id.call_get_request(
                url_path="listings/{}/calendar".format(self.property_id.guesty_id),
                params={
                    "from": self.start.strftime("%Y-%m-%d"),
                    "to": self.stop.strftime("%Y-%m-%d"),
                },
            )

            if success:
                prices = [calendar.get("price") for calendar in result]
                avg_price = sum(prices) / len(prices)
                self.price_unit = avg_price
