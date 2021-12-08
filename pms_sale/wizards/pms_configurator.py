# Copyright (c) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PMSConfigurator(models.TransientModel):
    _name = "pms.configurator"
    _description = "PMS Configurator"

    def _get_duration(self, start, stop):
        """ Get the duration value between the 2 given dates. """
        if not start or not stop:
            return 0
        duration = (stop - start).total_seconds() / (24 * 3600)
        return round(duration, 0)

    @api.depends("stop", "start")
    def _compute_duration(self):
        for reservation in self.with_context(dont_notify=True):
            reservation.duration = self._get_duration(
                reservation.start, reservation.stop
            )

    @api.depends("start", "duration")
    def _compute_stop(self):
        # stop and duration fields both depends on the start field.
        # But they also depends on each other.
        # When start is updated, we want to update the stop datetime based on
        # the *current* duration.
        # In other words, we want: change start => keep the duration fixed and
        # recompute stop accordingly.
        # However, while computing stop, duration is marked to be recomputed.
        # Calling `reservation.duration` would trigger its recomputation.
        # To avoid this we manually mark the field as computed.
        duration_field = self._fields["duration"]
        self.env.remove_to_compute(duration_field, self)
        for reservation in self:
            reservation.stop = reservation.start + timedelta(days=reservation.duration)

    @api.depends("guest_ids")
    def _compute_no_of_guests(self):
        self.no_of_guests = 0
        if self.guest_ids:
            self.no_of_guests = len(self.guest_ids)

    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    property_id = fields.Many2one("pms.property", string="Property")
    reservation_id = fields.Many2one(
        "pms.property.reservation", string="Reservation Type"
    )
    start = fields.Datetime(
        "From",
        required=True,
        default=fields.Date.today,
        help="Start date of the reservation",
    )
    stop = fields.Datetime(
        "To",
        required=True,
        default=fields.Date.today,
        compute="_compute_stop",
        readonly=False,
        store=True,
        help="Stop date of the reservation",
    )
    duration = fields.Integer(
        "Nights", compute="_compute_duration", store=True, readonly=False
    )
    no_of_guests = fields.Integer(
        "Number of Guests", compute="_compute_no_of_guests", store=True
    )
    guest_ids = fields.One2many(
        "pms.reservation.guest.wizard", "configurator_id", string="Guests"
    )

    @api.onchange("property_id")
    def onchange_property_id(self):
        user_tz = self.env.user.tz or "UTC"
        utc = pytz.timezone("UTC")
        timezone = pytz.timezone(user_tz)
        if (
            self.property_id
            and self.start
            and self.stop
            and self.property_id.checkin
            and self.property_id.checkout
        ):
            start_datetime = (
                str(self.start.date())
                + " "
                + str(timedelta(hours=self.property_id.checkin))
            )
            with_timezone = timezone.localize(
                datetime.strptime(start_datetime, DEFAULT_SERVER_DATETIME_FORMAT)
            )
            start_datetime = with_timezone.astimezone(utc)
            self.start = start_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            end_datetime = (
                str(self.stop.date())
                + " "
                + str(timedelta(hours=self.property_id.checkout))
            )
            with_timezone = timezone.localize(
                datetime.strptime(end_datetime, DEFAULT_SERVER_DATETIME_FORMAT)
            )
            end_datetime = with_timezone.astimezone(utc)
            self.stop = end_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        else:
            self.start = self.start.date()
            self.stop = self.stop.date()

    @api.constrains("property_id", "no_of_guests")
    def _check_max_no_of_guests(self):
        for configurator in self:
            if configurator.no_of_guests > configurator.property_id.no_of_guests:
                raise ValidationError(
                    _(
                        "%s of guests is lower than the %s of guests of the property."
                        % (
                            configurator.no_of_guests,
                            configurator.property_id.no_of_guests,
                        )
                    )
                )


class PMSReservationGuestWizard(models.TransientModel):
    _name = "pms.reservation.guest.wizard"
    _description = "PMS Reservation guest"

    name = fields.Char(string="Name", required=True)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    configurator_id = fields.Many2one("pms.configurator", string="Configurator")
    partner_id = fields.Many2one("res.partner", string="Partner")

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.name = self.partner_id.name
            self.phone = self.partner_id.phone
            self.email = self.partner_id.email
