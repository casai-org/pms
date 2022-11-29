# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import datetime
import json
import logging

import pytz
import requests

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

_log = logging.getLogger(__name__)

_tzs = [
    (tz, tz)
    for tz in sorted(
        pytz.all_timezones, key=lambda tz: tz if not tz.startswith("Etc/") else "_"
    )
]


def _tz_get(self):
    return _tzs


class BackendGuesty(models.Model):
    _name = "backend.guesty"
    _description = "Guesty Backend"

    guesty_account_id = fields.Char()
    guesty_environment = fields.Selection(
        [("prod", "Production V2"), ("dev", "Development V2")],
        default="dev",
        required=True,
    )

    name = fields.Char(required=True)
    reservation_pull_start_date = fields.Datetime()

    cleaning_product_id = fields.Many2one("product.product")
    extra_product_id = fields.Many2one("product.product")
    reservation_product_id = fields.Many2one("product.product")

    crm_lead_rule_ids = fields.One2many("crm.lead.rule", "backend_id")
    is_default = fields.Boolean(default=False)

    active = fields.Boolean(default=True, required=True)
    currency_id = fields.Many2one("res.currency")
    timezone = fields.Selection(_tz_get, string="Timezone")

    stage_canceled_id = fields.Many2one(
        "pms.stage", domain=[("stage_type", "=", "reservation")]
    )
    stage_inquiry_id = fields.Many2one(
        "pms.stage", domain=[("stage_type", "=", "reservation")]
    )
    stage_reserved_id = fields.Many2one(
        "pms.stage", domain=[("stage_type", "=", "reservation")]
    )
    stage_confirmed_id = fields.Many2one(
        "pms.stage", domain=[("stage_type", "=", "reservation")]
    )

    cancel_expired_quotes = fields.Boolean(default=False)

    custom_field_ids = fields.One2many("pms.backend.custom_field", "backend_id")
    enable_guesty_discount = fields.Boolean(default=False)
    company_id = fields.Many2one("res.company")

    credentials_id = fields.Many2one("backend.guesty.credentials")

    def set_as_default(self):
        self.sudo().search([("is_default", "=", True)]).write({"is_default": False})
        self.write({"is_default": True})

        self.env.company.guesty_backend_id = self.id

    def sync_account_info(self):
        self.ensure_one()
        if not self.guesty_account_id:
            raise UserError(_("Please set the Guesty account ID"))

        success, response = self.credentials_id._get_account_info()

        if success:
            # general data
            _id = response.get("_id")
            _tz = response.get("timezone")
            _currency = response.get("currency")

            currency = self.env["res.currency"].search(
                [("name", "=", _currency)], limit=1
            )
            payload = {
                "guesty_account_id": _id,
                "active": True,
                "currency_id": currency.id,
            }

            if _tz:
                payload["timezone"] = _tz

            if "timezone" not in payload and not self.timezone:
                payload["timezone"] = self.env.user.tz

            if not self.stage_canceled_id:
                payload["stage_canceled_id"] = self.env.ref(
                    "pms_sale.pms_stage_cancelled", raise_if_not_found=False
                ).id

            if not self.stage_inquiry_id:
                payload["stage_inquiry_id"] = self.env.ref(
                    "pms_sale.pms_stage_new", raise_if_not_found=False
                ).id

            if not self.stage_reserved_id:
                payload["stage_reserved_id"] = self.env.ref(
                    "pms_sale.pms_stage_booked", raise_if_not_found=False
                ).id

            if not self.stage_confirmed_id:
                payload["stage_confirmed_id"] = self.env.ref(
                    "pms_sale.pms_stage_confirmed", raise_if_not_found=False
                ).id

            if not self.reservation_product_id:
                payload["reservation_product_id"] = (
                    self.env["product.product"]
                    .search([("reservation_ok", "=", True)], limit=1)
                    .id
                )

            self.write(payload)

            # custom fields
            custom_fields = response.get("customFields", [])
            for custom_field in custom_fields:
                _log.info("Trying to create custom field %s", custom_field)
                custom_field_obj = self.env["pms.guesty.custom_field"].search(
                    [("external_id", "=", custom_field["_id"])]
                )
                if not custom_field_obj.exists():
                    self.env["pms.guesty.custom_field"].sudo().create(
                        {
                            "name": custom_field["displayName"],
                            "external_id": custom_field["_id"],
                        }
                    )

    def check_credentials(self):
        return self.credentials_id.check_credentials()

    def reset_credentials(self):
        if self.env.company.guesty_backend_id.id == self.id:
            self.env.company.guesty_backend_id = False

        self.write({"active": False, "is_default": False})

    def guesty_search_create_customer(self, partner):
        guesty_partner = self.env["res.partner.guesty"].search(
            [("partner_id", "=", partner.id)], limit=1
        )

        first_name, last_name = partner.split_name()

        if not guesty_partner:
            # create on guesty
            body = {
                "firstName": first_name,
                "lastName": last_name,
                "fullName": partner.name,
                "email": partner.email,
            }

            if partner.phone or partner.mobile:
                body["phone"] = partner.phone or partner.mobile

            success, res = self.call_post_request(url_path="guests", body=body)

            if not success:
                raise UserError(_("Unable to create customer"))

            guesty_id = res.get("_id")
            customer = self.env["res.partner.guesty"].create(
                {"partner_id": partner.id, "guesty_id": guesty_id}
            )

            return customer
        else:
            guesty_partner.guesty_push_update()
            return guesty_partner

    def guesty_search_pull_customer(self, guesty_id):
        """
        Method to search a guesty customer into odoo
        Docs: https://docs.guesty.com/#retrieve-a-guest
        :param str guesty_id: Guesty customer ID
        :return models.Model(res.partner.guesty):
        """
        # search for a guesty customer in the odoo database into the res.partner.guesty
        # model if we don't found them, we request to get the customer data from guesty
        # and store it into odoo
        if guesty_id is None:
            return

        guesty_partner = self.env["res.partner.guesty"].search(
            [("guesty_id", "=", guesty_id)], limit=1
        )
        if not guesty_partner:
            # get data from guesty
            success, res = self.call_get_request(url_path="guests/{}".format(guesty_id))

            if not success:
                raise UserError(_("Failed to get customer data from guesty"))

            customer_name = res.get("fullName")
            if not customer_name:
                customer_name = res.get("firstName")
                if customer_name and res.get("lastName"):
                    customer_name = "{} {}".format(customer_name, res.get("lastName"))

            if not customer_name:
                customer_name = "Anonymous Customer"

            body_payload = {
                "name": customer_name,
                "email": res.get("email"),
                "phone": res.get("phone"),
            }

            hometown = res.get("hometown")
            if hometown:
                home_town_split = hometown.split(", ")
                if len(home_town_split) >= 2:
                    city, country_name = home_town_split[0:2]
                    country = self.env["res.country"].search(
                        [("name", "=", country_name)], limit=1
                    )
                    if country.exists():
                        body_payload["country_id"] = country.id
                else:
                    city = hometown
                body_payload["city"] = city

            if "city" not in body_payload:
                body_payload["city"] = "ND"

            if "country_id" not in body_payload:
                body_payload["country_id"] = self.env.ref(
                    "base.mx", raise_if_not_found=False
                ).id

            base_partner = self.env["res.partner"].create(body_payload)

            customer = self.env["res.partner.guesty"].create(
                {"partner_id": base_partner.id, "guesty_id": guesty_id}
            )

            return customer
        else:
            return guesty_partner

    def download_reservations(self):
        """
        Method to download reservations from guesty
        Docs: https://docs.guesty.com/#search-reservations
        :return:
        """
        reservation_status = [
            "inquiry",
            "declined",
            "expired",
            "canceled",
            "closed",
            "reserved",
            "confirmed",
            "checked_in",
            "checked_out",
            "awaiting_payment",
        ]
        filters = [{"field": "status", "operator": "$in", "value": reservation_status}]
        if self.reservation_pull_start_date:
            filters.append(
                {
                    "field": "lastUpdatedAt",
                    "operator": "$gte",
                    "value": self.reservation_pull_start_date.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    ),
                }
            )

        params = {
            "filters": json.dumps(filters),
            "sort": "lastUpdatedAt",
            "fields": " ".join(
                [
                    "status",
                    "checkIn",
                    "checkOut",
                    "listingId",
                    "guestId",
                    "listing.nickname",
                    "lastUpdatedAt",
                    "money",
                    "nightsCount",
                ]
            ),
        }

        success, res = self.call_get_request(url_path="reservations", params=params)

        if not success:
            _log.error(res.content)
            raise ValidationError(_("Unable to sync data"))

        records = res.get("results", [])
        reservation_last_date = None
        for reservation in records:
            self.env["pms.reservation"].with_delay().guesty_pull_reservation(
                self, reservation
            )
            _reservation_update_date = reservation.get("lastUpdatedAt")
            if _reservation_update_date:
                _reservation_update_date = _reservation_update_date[0:19]
                _reservation_update_date = datetime.datetime.strptime(
                    _reservation_update_date, "%Y-%m-%dT%H:%M:%S"
                )
                if (
                    not reservation_last_date
                    or _reservation_update_date > reservation_last_date
                ):
                    reservation_last_date = _reservation_update_date

        if reservation_last_date:
            self.reservation_pull_start_date = reservation_last_date

    def download_calendars(self):
        date_now = datetime.datetime.now()
        date_limit = date_now + datetime.timedelta(days=180)

        date_start = date_now.strftime("%Y-%m-%d")
        date_stop = date_limit.strftime("%Y-%m-%d")

        properties = self.env["pms.property"].search([("guesty_id", "!=", False)])
        time_sleep = 0.0
        for property_id in properties:
            time_sleep += 0.5
            self.env["pms.guesty.calendar"].with_delay(time_sleep).guesty_pull_calendar(
                self, property_id, date_start, date_stop
            )

    def call_get_request(
        self, url_path, params=None, skip=0, limit=25, success_codes=None, paginate=True
    ):
        return self.credentials_id.call_get_request(
            url_path,
            params=params,
            skip=skip,
            limit=limit,
            success_codes=success_codes,
            paginate=paginate,
        )

    def call_post_request(self, url_path, body):
        return self.credentials_id.call_post_request(url_path, body)

    def call_put_request(self, url_path, body):
        return self.credentials_id.call_put_request(url_path, body)

    def download_properties(self):
        property_ids = self.env["pms.property"].sudo().search([])

        skip = 0
        while True:
            success, res = self.call_get_request(
                url_path="listings",
                params={
                    "fields": " ".join(
                        [
                            "title",
                            "nickname",
                            "accountId",
                            "address.city",
                            "active",
                            "isListed",
                        ]
                    ),
                },
                limit=100,
                skip=skip,
            )

            skip += 100

            if success:
                result = res.get("results", [])
                for record in result:
                    self.env["pms.guesty.listing"].guesty_pull_listing(record)

                if len(result) == 0:
                    break
            else:
                break

        for property_id in property_ids.filtered(lambda x: x.guesty_id):
            listing_id = self.env["pms.guesty.listing"].search(
                [("external_id", "=", property_id.guesty_id)], limit=1
            )
            if listing_id:
                property_id.guesty_listing_ids += listing_id

        for property_id in property_ids.filtered(lambda x: not x.guesty_id):
            record_match = self.env["pms.guesty.listing"].search(
                [("name", "=", property_id.ref)]
            )
            if record_match:
                property_id.guesty_id = record_match.external_id
                property_id.guesty_listing_ids += record_match

    def guesty_get_calendar_info(self, check_in, check_out, property_ids):
        listing_ids = property_ids.mapped("guesty_id")
        result = {}
        real_stop_date = check_out - datetime.timedelta(days=1)
        for listing_id in listing_ids:
            # todo: Fix Calendar
            success, res = self.call_get_request(
                url_path="availability-pricing/api/calendar/listings/{}".format(
                    listing_id
                ),
                paginate=False,
                params={"startDate": check_in, "endDate": real_stop_date},
            )
            if success:
                calendar_data = res.get("data", {}).get("days", [])
                if len(calendar_data) == 0:
                    raise ValidationError(_("Unable to validate dates in guesty"))

                currency = calendar_data[0]["currency"]
                avg_price = sum(a.get("price") for a in calendar_data) / len(
                    calendar_data
                )
                status_list = [a["status"] for a in calendar_data]
                result[listing_id] = {
                    "currency": currency,
                    "price": avg_price,
                    "status": list(set(status_list)),
                }

        return result

    def download_pictures(self):
        result_token = requests.post(
            "https://test-api.casai.com/auth/",
            headers={"Content-Type": "application/json"},
            json={},
        )

        if result_token.status_code not in [200, 201]:
            raise ValidationError(_("unable to call api"))

        auth_data = result_token.json()
        token_value = auth_data.get("token")

        if not token_value:
            raise ValidationError(_("Unable to load token"))

        listing_ids = (
            self.env["pms.property"]
            .sudo()
            .search([("guesty_id", "!=", False)], limit=10)
        )

        for listing in listing_ids:
            listing_url = "https://test-api.casai.com/listings/{}/".format(
                listing.guesty_id
            )
            res = requests.get(
                listing_url, headers={"Authorization": "Token {}".format(token_value)}
            )
            if res.status_code not in [200, 201]:
                continue

            data = res.json()
            _Picture = self.env["pms.property.picture"].sudo()
            for _pic in data.get("pictures", []):
                thumb = _pic["thumbnail"].replace(".webp", ".jpg")
                large = _pic["large"].replace(".webp", ".jpg")
                _search = _Picture.search([("external_id", "=", _pic["id"])], limit=1)

                _log.info("Uploading: {}".format(listing.guesty_id))

                _payload = {
                    "name": _pic["caption"],
                    "url_thumbnail": thumb,
                    "url_large": large,
                    "property_id": listing.id,
                }
                if not _search.exists():
                    img_req = requests.get(thumb)
                    data = img_req.content
                    data = base64.b64encode(data)
                    _payload["original_data"] = data
                    _payload["external_id"] = _pic["id"]
                    _Picture.create(_payload)
                else:
                    _search.write(_payload)

            # Update data
            if not listing.ota_description:
                listing.write({"ota_description": data["publicdescription_space"]})

            if listing.name != data["casai_listing"]["casai_title"]:
                listing.write({"name": data["casai_listing"]["casai_title"]})

            if listing.ref != data["nickname"]:
                listing.write({"ref": data["nickname"]})
