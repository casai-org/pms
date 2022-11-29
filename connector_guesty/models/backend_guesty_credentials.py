# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import datetime
import logging
from urllib.parse import urlencode

import pytz
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_log = logging.getLogger(__name__)

_tzs = [
    (tz, tz)
    for tz in sorted(
        pytz.all_timezones, key=lambda tz: tz if not tz.startswith("Etc/") else "_"
    )
]


def _tz_get(self):
    return _tzs


class BackendGuestyCredentials(models.Model):
    _name = "backend.guesty.credentials"

    name = fields.Char(required=True)
    guesty_environment = fields.Selection(
        [("prod", "Production V2"), ("dev", "Development V2")],
        default="dev",
        required=True,
    )

    guesty_account_id = fields.Char()

    api_key = fields.Char(required=True)
    api_secret = fields.Char(required=True)

    refresh_token = fields.Text()
    token_expiration = fields.Datetime()

    api_url = fields.Char(required=True, compute="_compute_environment_fields")
    base_url = fields.Char(compute="_compute_environment_fields", required=True)
    auth_url = fields.Char(compute="_compute_environment_fields", required=True)

    auth_type = fields.Selection(
        [("basic", "Basic Auth"), ("oauth2", "oAuth 2.0")],
        default="basic",
        required=True,
    )

    refresh_token = fields.Text()
    token_expiration = fields.Datetime()

    @api.depends("guesty_environment")
    def _compute_environment_fields(self):
        # noinspection PyTypeChecker
        for record in self:
            map_values = self._map_environment_data(
                record.guesty_environment, record.auth_type
            )
            for field_name in map_values:
                record[field_name] = map_values[field_name]

    def _map_environment_data(self, guesty_env, auth_type="basic"):
        if guesty_env == "prod" and auth_type == "basic":
            return {
                "api_url": "https://api.guesty.com/api/v2",
                "base_url": "https://app.guesty.com",
            }
        elif guesty_env == "prod" and auth_type == "oauth2":
            return {
                "api_url": "https://open-api.guesty.com/v1",
                "base_url": "https://app.guesty.com",
                "auth_url": "https://open-api.guesty.com/oauth2/token",
            }
        elif guesty_env == "dev" and auth_type == "oauth2":
            return {
                "api_url": "https://open-api-sandbox.guesty.com/v1",
                "base_url": "https://app-sandbox.guesty.com",
                "auth_url": "https://open-api-sandbox.guesty.com/oauth2/token",
            }
        else:
            return {
                "api_url": "https://api.sandbox.guesty.com/api/v2",
                "base_url": "https://app-sandbox.guesty.com",
            }

    def _get_account_info(self):
        success, result = self.call_get_request("accounts/me", limit=1)
        return success, result

    @api.model
    def create(self, values):
        rs = super().create(values)
        rs.check_credentials()
        return rs

    def write(self, values):
        rs = super().write(values)
        fields_to_ckeck = ["api_key", "api_secret", "auth_type"]

        if any([a in values for a in fields_to_ckeck]):
            for record in self:
                record.check_credentials()
        return rs

    def check_credentials(self):
        # url to validate the credentials
        # this endpoint will search a list of users, it may be empty if the api key
        # does not have permissions to list the users, but it should be a 200 response
        # Note: Guesty does not provide a way to validate credentials
        success, result = self._get_account_info()
        if success:
            self.write({"guesty_account_id": result["_id"]})
            return True
        else:
            raise UserError(_("Connection Test Failed!"))

    def get_auth_token(self):
        """
        Obtain a new token
        """
        current_date = datetime.datetime.now()

        if self.token_expiration and self.token_expiration > current_date:
            return self.refresh_token

        payload = {
            "grant_type": "client_credentials",
            "scope": "open-api",
            "client_secret": self.api_secret,
            "client_id": self.api_key,
        }

        data = urlencode(payload)

        request_token = requests.post(
            url=self.auth_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data,
        )

        if request_token.status_code == 200:
            response_data = request_token.json()
            token, expire = response_data["access_token"], response_data["expires_in"]
            expiration = current_date + datetime.timedelta(seconds=expire)

            self.refresh_token = token
            self.token_expiration = expiration
            return response_data["access_token"]

        else:
            return None

    def call_get_request(
        self, url_path, params=None, skip=0, limit=25, success_codes=None, paginate=True
    ):
        if success_codes is None:
            success_codes = [200, 201]

        if params is None:
            params = {}

        if paginate:
            params.update({"skip": str(skip), "limit": str(limit)})

        url = "{}/{}".format(self.api_url, url_path)
        try:
            _log.info("Calling GET request to {}".format(url))
            if self.auth_type == "oauth2":
                access_token = self.get_auth_token()
                if not access_token:
                    return False, None

                result = requests.get(
                    url=url,
                    params=params,
                    headers={"Authorization": "Bearer {}".format(access_token)},
                )

            else:
                result = requests.get(
                    url=url, params=params, auth=(self.api_key, self.api_secret)
                )

            if result.status_code in success_codes:
                return True, result.json()

            _log.error(result.content)
        except Exception as ex:
            _log.error(ex)

        return False, None

    def call_post_request(self, url_path, body):
        url = "{}/{}".format(self.api_url, url_path)
        _log.info("Calling POST request to {}".format(url))

        if self.auth_type == "oauth2":
            access_token = self.get_auth_token()

            if not access_token:
                return False, None

            result = requests.post(
                url=url,
                json=body,
                headers={"Authorization": "Bearer {}".format(access_token)},
            )

        else:
            result = requests.post(
                url=url, json=body, auth=(self.api_key, self.api_secret)
            )

        if result.status_code == 200:
            return True, result.json()
        else:
            _log.error(result.content)
            return False, result.content.decode()

    def call_put_request(self, url_path, body):
        url = "{}/{}".format(self.api_url, url_path)
        _log.info("Calling PUT request to {}".format(url))

        if self.auth_type == "oauth2":
            access_token = self.get_auth_token()

            if not access_token:
                return False, None

            result = requests.put(
                url=url,
                json=body,
                headers={"Authorization": "Bearer {}".format(access_token)},
            )
        else:
            result = requests.put(
                url=url, json=body, auth=(self.api_key, self.api_secret)
            )

        if result.status_code == 200:
            if result.content.decode("utf-8") == "ok":
                return True, result.content.decode("utf-8")
            else:
                return True, result.json()
        else:
            _log.error(result.content)
            return False, result.content.decode("utf-8")
