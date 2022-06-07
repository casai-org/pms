# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import datetime
import logging

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_log = logging.getLogger(__name__)


class PmsGuestyCalendar(models.Model):
    _name = "pms.guesty.calendar"
    _description = "Guesty Calendar"
    _rec_name = "price"

    listing_id = fields.Char(required=True)
    listing_date = fields.Date(required=True)
    state = fields.Selection(
        [
            ("available", _("Available")),
            ("unavailable", _("Unavailable")),
            ("reserved", _("Reserved")),
            ("booked", _("Booked")),
        ],
        required=True,
    )

    price = fields.Float(required=True)
    currency = fields.Char(required=True)
    note = fields.Text()

    property_id = fields.Many2one("pms.property", required=True)

    date_start = fields.Datetime(compute="_compute_full_date", store=True)
    date_stop = fields.Datetime(compute="_compute_full_date", store=True)
    color = fields.Integer(compute="_compute_full_date", store=True)

    _sql_constraints = [
        (
            "unique_listing_date",
            "unique(listing_id, listing_date)",
            _("You cannot have dates duplicated by listing"),
        )
    ]

    @api.depends("listing_date", "state")
    def _compute_full_date(self):
        _log.info(self.env.context)
        for record in self:
            tz = pytz.timezone(record.property_id.tz)
            start = datetime.datetime.combine(
                record.listing_date, datetime.datetime.min.time()
            )
            start = tz.localize(start).astimezone(pytz.UTC).replace(tzinfo=None)
            # _log.info(start)

            stop = datetime.datetime.combine(
                record.listing_date, datetime.datetime.max.time()
            )
            stop = tz.localize(stop).astimezone(pytz.UTC).replace(tzinfo=None)

            record.date_start = start
            record.date_stop = stop
            record.color = 10 if record.state == "available" else 1

    def guesty_pull_calendar(self, backend, property_id, start_date, stop_date):
        # todo: Fix Calendar
        success, result = backend.call_get_request(
            url_path="availability-pricing/api/calendar/listings/{}".format(
                property_id.guesty_id
            ),
            paginate=False,
            params={"startDate": start_date, "endDate": stop_date},
        )

        if success:
            calendar_data = result.get("data", {}).get("days", [])
            for record in calendar_data:
                calendar_id = self.sudo().search(
                    [
                        ("listing_id", "=", property_id.guesty_id),
                        ("listing_date", "=", record.get("date")),
                    ]
                )

                payload = {
                    "listing_id": property_id.guesty_id,
                    "listing_date": record.get("date"),
                    "state": record.get("status"),
                    "price": record.get("price"),
                    "currency": record.get("currency"),
                    "note": record.get("note"),
                    "property_id": property_id.id,
                }

                if not calendar_id.exists():
                    self.sudo().create(payload)
                else:
                    calendar_id.sudo().write(payload)
        else:
            raise UserError(_("Failed to sync calendars"))

    def compute_price(self, property_id, start_date, end_date, currency):
        """
        Compute the price for a date range based on calendar prices
        :param Model(pms.property) property_id:
        :param Datetime start_date:
        :param Datetime end_date:
        :param str currency:
        :return:
        """
        utc = pytz.UTC
        tz = pytz.timezone(self.property_id.tz or "America/Mexico_City")
        start_date_localized = utc.localize(start_date).astimezone(tz)
        stop_date_localized = utc.localize(end_date).astimezone(tz)

        # remove 1 day because the checkout day is a day after
        real_end_date = stop_date_localized - datetime.timedelta(days=1)
        calendars = self.sudo().search(
            [
                ("property_id", "=", property_id.id),
                ("listing_date", ">=", start_date_localized.date()),
                ("listing_date", "<=", real_end_date.date()),
            ]
        )

        days_len = (stop_date_localized.date() - start_date_localized.date()).days
        if days_len != len(calendars):
            raise ValidationError(_("Invalid days range"))

        for calendar_day in calendars:
            _log.info(calendar_day.listing_date)
        raise ValidationError(_("Looks fine"))

    def guesty_pull_calendar_event(self, calendar_info):
        calendar_id = self.sudo().search(
            [
                ("listing_id", "=", calendar_info["listingId"]),
                ("listing_date", "=", calendar_info["date"]),
            ]
        )

        property_id = (
            self.env["pms.property"]
            .sudo()
            .search([("guesty_id", "=", calendar_info["listingId"])], limit=1)
        )

        if not property_id:
            raise ValidationError(_("Property not found"))

        payload = {
            "listing_id": calendar_info["listingId"],
            "listing_date": calendar_info["date"],
            "state": calendar_info["status"],
            "price": calendar_info["price"],
            "currency": calendar_info["currency"],
            "property_id": property_id.id,
        }

        if not calendar_id.exists():
            return self.sudo().create(payload)
        else:
            return calendar_id.sudo().write(payload)
