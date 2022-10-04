# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import datetime
import logging

import pytz

from odoo import _, fields, models

_log = logging.getLogger(__name__)


class WizCrmLeadNewReservation(models.TransientModel):
    _name = "wiz.crm.lead.new.reservation"
    _description = "New Reservation Wizard"

    crm_lead_id = fields.Many2one("crm.lead")
    check_in = fields.Date(required=True)
    check_out = fields.Date(required=True)
    price_list_id = fields.Many2one("product.pricelist", required=True)

    state = fields.Selection(
        [("new", _("New")), ("availability", _("Check Availability"))], default="new"
    )

    discount = fields.Float(string="Discount %")
    cleaning_fee_price = fields.Float(string="Cleaning Fee $")

    available_ids = fields.Many2many("crm.listing.availability")

    def action_cancel_soft_reset(self):
        self.write({"state": "new"})

        action = self.crm_lead_id.action_new_quotation_reservation()
        action["res_id"] = self.id
        return action

    def action_check_availability(self):
        # guesty_listing_list = self.execute_availability_query()
        # _search_props = self.env["pms.property"].search(
        #     [("guesty_id", "!=", False), ("guesty_id", "in", guesty_listing_list)]
        # )
        #
        # calendar_result = self.env.company.guesty_backend_id.guesty_get_calendar_info(
        #     self.check_in, self.check_out, _search_props
        # )
        #
        # calendar = [
        #     {"listing": key, "info": calendar_result[key]}
        #     for key in calendar_result
        #     if len(calendar_result[key]["status"]) == 1
        #     and "available" in calendar_result[key]["status"]
        # ]
        #
        # calendar_ids = [a["listing"] for a in calendar]
        # _search_props = self.env["pms.property"].search(
        #     [("guesty_id", "!=", False), ("guesty_id", "in", calendar_ids)]
        # )

        query = """
        select t.* from (
            select min(id) as id, listing_id, state, count(*) as "count",
                min(listing_date) as start_date, max(listing_date) as end_date from (
            select id, listing_id, state, listing_date,
            date(listing_date) - row_number() over (partition by listing_id,
                state order by date(listing_date)) * interval '1 day' "filter"
            from pms_guesty_calendar pgc
            where pgc.listing_date between %(checkin)s and %(checkout)s
            ) t1
            group by listing_id, state, filter
            order by listing_id, min(listing_date)
        ) as t
        where t.state = 'available'
        and t.start_date >= %(checkin)s and t.end_date <= %(checkout)s
        """

        self.env.cr.execute(
            query, {"checkin": self.check_in, "checkout": self.check_out}
        )
        results = self.env.cr.dictfetchall()

        _log.info(results)

        guesty_ids = [a["listing_id"] for a in results]

        _search_props = self.env["pms.property"].search(
            [("guesty_id", "in", guesty_ids)]
        )

        self.env["crm.listing.availability"].sudo().search(
            [("crm_lead_id", "=", self.crm_lead_id.id)]
        ).unlink()

        no_nights = (self.check_out - self.check_in).days

        for _prop in _search_props:
            _product = (
                self.env.company.guesty_backend_id.reservation_product_id.with_context(
                    pricelist=self.price_list_id.id,
                    property_id=_prop,
                    reservation_start=self.check_in,
                    reservation_stop=self.check_out,
                    reservation_date=datetime.datetime.now(),
                )
            )

            # noinspection PyProtectedMember
            _product.with_context(price_source="local")._compute_product_price()
            custom_price = _product.price

            self.env["crm.listing.availability"].sudo().create(
                {
                    "crm_lead_id": self.crm_lead_id.id,
                    "property_id": _prop.id,
                    "price": custom_price,
                    "currency": self.price_list_id.currency_id.name,
                    "no_nights": no_nights,
                    "total_price": no_nights * custom_price,
                }
            )

        self.write({"state": "availability"})
        action = self.crm_lead_id.action_new_quotation_reservation()
        action["res_id"] = self.id
        return action

    @staticmethod
    def compute_default_ci_co(date_input, time_input):
        if date_input and time_input:
            date_hour, date_minute = divmod(
                time_input * 60, 60
            )  # converts like 11.5 to 11:30
            date_time = datetime.time(int(date_hour), int(date_minute))
            final_date = datetime.datetime.combine(date_input, date_time)
            return final_date
        elif date_input:
            return datetime.datetime.combine(date_input, datetime.datetime.min.time())

        else:
            return datetime.datetime.combine(
                datetime.datetime.today().date(), datetime.datetime.min.time()
            )

    def action_create_quotation(self):
        _log.info(self.available_ids)
        so_ids = []
        for _self in self.available_ids:
            backend = _self.env.company.guesty_backend_id
            reservation_product_id = backend.reservation_product_id

            if _self.property_id.reservation_ids:
                guesty_price_id = _self.property_id.reservation_ids.filtered(
                    lambda s: s.currency_id.id == backend.currency_id.id
                )
                utc = pytz.UTC
                tz = pytz.timezone(backend.timezone)

                ci = self.compute_default_ci_co(
                    self.check_in, _self.property_id.checkin
                )
                co = self.compute_default_ci_co(
                    self.check_out, _self.property_id.checkout
                )

                ci = tz.localize(ci).astimezone(utc).replace(tzinfo=None)
                co = tz.localize(co).astimezone(utc).replace(tzinfo=None)

                if reservation_product_id:
                    order_lines = [
                        (
                            0,
                            False,
                            {
                                "product_uom_qty": _self.no_nights,
                                "price_unit": _self.price,
                                "product_id": reservation_product_id.id,
                                "reservation_id": guesty_price_id.id,
                                "property_id": _self.property_id.id,
                                "start": ci,
                                "stop": co,
                                "discount": self.discount,
                            },
                        )
                    ]

                    if self.cleaning_fee_price > 0:
                        order_lines.append(
                            (
                                0,
                                False,
                                {
                                    "product_id": backend.cleaning_product_id.id,
                                    "name": backend.cleaning_product_id.name,
                                    "product_uom_qty": 1,
                                    "price_unit": self.cleaning_fee_price,
                                },
                            )
                        )

                    so = self.env["sale.order"].create(
                        {
                            "partner_id": _self.crm_lead_id.partner_id.id,
                            "opportunity_id": _self.crm_lead_id.id,
                            "pricelist_id": self.price_list_id.id,
                            "order_line": order_lines,
                        }
                    )

                    so_ids.append(so.id)

        return {
            "type": "ir.actions.act_window",
            "name": _("Quotations"),
            "res_model": "sale.order",
            "view_mode": "tree,form",
            "domain": [("id", "in", so_ids)],
        }


class CRMListingAvailability(models.Model):
    _name = "crm.listing.availability"
    _description = "Listing Availability"

    crm_lead_id = fields.Many2one("crm.lead")
    property_id = fields.Many2one("pms.property")

    # related
    city = fields.Char(related="property_id.city", store=True)
    country_id = fields.Many2one(
        "res.country", related="property_id.country_id", store=True
    )

    price = fields.Float()
    currency = fields.Char()
    no_nights = fields.Integer()
    total_price = fields.Float()
