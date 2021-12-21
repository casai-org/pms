# Copyright (c) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    property_id = fields.Many2one("pms.property", string="Property")
    reservation_id = fields.Many2one(
        "pms.property.reservation", string="Reservation Type"
    )
    reservation_ok = fields.Boolean(
        related="product_id.reservation_ok", readonly=True, string="Is Reservation?"
    )
    start = fields.Datetime("From")
    stop = fields.Datetime("To")
    no_of_guests = fields.Integer("Number of Guests")
    guest_ids = fields.One2many(
        "pms.reservation.guest", "order_line_id", string="Guests"
    )
    pms_reservation_id = fields.Many2one("pms.reservation", string="Reservation")

    @api.onchange("reservation_id", "no_of_guests")
    def _onchange_reservation_id(self):
        # we call this to force update the default name
        self.product_id_change()

    def get_sale_order_line_multiline_description_sale(self, product):
        if self.reservation_id:
            return (
                "".join(
                    [
                        self.reservation_id.display_name,
                        " (",
                        str(self.no_of_guests),
                        " Guests)",
                    ]
                )
                + self._get_sale_order_line_multiline_description_variants()
            )
        else:
            return super(
                SaleOrderLine, self
            ).get_sale_order_line_multiline_description_sale(product)

    @api.model
    def create(self, values):
        rec = super(SaleOrderLine, self).create(values)
        if (
            values.get("product_id")
            and values.get("reservation_id")
            and values.get("property_id")
        ):
            reservation_vals = {
                "partner_id": rec.order_id.partner_id.id,
                "sale_order_id": rec.order_id.id,
                "sale_order_line_id": rec.id,
            }
            reservation = self._create_pms_reservation(values, reservation_vals)
            if reservation:
                rec.pms_reservation_id = reservation.id
        return rec

    def write(self, values):
        rec = super(SaleOrderLine, self).write(values)
        if values.get("product_id") and self.product_id.reservation_ok:
            reservation_vals = {
                "partner_id": self.order_id.partner_id.id,
                "sale_order_id": self.order_id.id,
                "sale_order_line_id": self.id,
            }
            reservation = self._create_pms_reservation(values, reservation_vals)
            if reservation:
                self.pms_reservation_id = reservation.id
        return rec

    def _create_pms_reservation(self, values, reservation_vals):
        reservation = False
        if reservation_vals:
            reservation_vals.update(
                {
                    "date": datetime.now(),
                    "property_id": values.get("property_id") or self.property_id.id,
                    "start": values.get("start") or self.start or datetime.now(),
                    "stop": values.get("stop") or self.stop or datetime.now(),
                    "guest_ids": values.get("guest_ids") or False,
                }
            )
            reservation = self.env["pms.reservation"].create(reservation_vals)
        return reservation

    def unlink(self):
        if self.product_id.reservation_ok and self.pms_reservation_id:
            self.pms_reservation_id.stage_id = self.env.ref(
                "pms_sale.pms_stage_cancelled", raise_if_not_found=False
            ).id
        return super(SaleOrderLine, self).unlink()

    @api.onchange("product_id")
    def product_id_change(self):
        super(SaleOrderLine, self).product_id_change()
        if self.reservation_id:
            self.price_unit = self.reservation_id.price
            if self.order_id.pricelist_id:
                product = self.product_id.with_context(
                    lang=self.order_id.partner_id.lang,
                    partner=self.order_id.partner_id,
                    quantity=self.product_uom_qty,
                    date=self.order_id.date_order,
                    pricelist=self.order_id.pricelist_id.id,
                    uom=self.product_uom.id,
                    fiscal_position=self.env.context.get("fiscal_position"),
                )
                price = self.env["account.tax"]._fix_tax_included_price_company(
                    self._get_display_price(product),
                    product.taxes_id,
                    self.tax_id,
                    self.company_id,
                )
                if price != product.lst_price:
                    self.price_unit = price

    @api.onchange("product_uom", "product_uom_qty")
    def product_uom_change(self):
        super(SaleOrderLine, self).product_uom_change()
        if self.reservation_id:
            self.price_unit = self.reservation_id.price
            if self.order_id.pricelist_id:
                product = self.product_id.with_context(
                    lang=self.order_id.partner_id.lang,
                    partner=self.order_id.partner_id,
                    quantity=self.product_uom_qty,
                    date=self.order_id.date_order,
                    pricelist=self.order_id.pricelist_id.id,
                    uom=self.product_uom.id,
                    fiscal_position=self.env.context.get("fiscal_position"),
                )
                price = self.env["account.tax"]._fix_tax_included_price_company(
                    self._get_display_price(product),
                    product.taxes_id,
                    self.tax_id,
                    self.company_id,
                )
                if price != product.lst_price:
                    self.price_unit = price

    def _prepare_invoice_line(self, **optional_values):
        result = super()._prepare_invoice_line(**optional_values)
        self.ensure_one()
        if self.pms_reservation_id and self.property_id:
            result.update(
                {
                    "pms_reservation_id": self.pms_reservation_id.id,
                    "property_ids": [(6, 0, self.property_id.ids)],
                }
            )
        return result