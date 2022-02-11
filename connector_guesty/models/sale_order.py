# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import api, models

_log = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def create(self, values):
        return super().create(values)

    def write(self, values):
        res = super().write(values)
        if (
            self.company_id.guesty_backend_id
            and not self.env.context.get("ignore_guesty_push", False)
            and "order_line" in values
        ):
            for sale in self:
                reservation = self.env["pms.reservation"].search(
                    [("sale_order_id", "=", sale.id)]
                )
                if reservation and reservation.guesty_id:
                    reservation.with_delay().guesty_push_reservation_update()
        return res

    def action_cancel(self):
        stage_ids = [
            self.env.ref("pms_sale.pms_stage_new", raise_if_not_found=False).id,
            self.env.ref("pms_sale.pms_stage_booked", raise_if_not_found=False).id,
            self.env.ref("pms_sale.pms_stage_confirmed", raise_if_not_found=False).id,
        ]
        reservation_ids = self.env["pms.reservation"].search(
            [("sale_order_id", "=", self.id), ("stage_id", "in", stage_ids)]
        )
        reservation_ids.action_cancel()
        return super().action_cancel()
