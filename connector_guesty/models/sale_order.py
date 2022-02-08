# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import models

_log = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

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

    def _get_share_url(
        self, redirect=False, signup_partner=False, pid=None, share_token=True
    ):
        _log.info("redirect: {}".format(redirect))
        _log.info(share_token)
        return super()._get_share_url(
            redirect=redirect,
            signup_partner=signup_partner,
            pid=pid,
            share_token=share_token,
        )
