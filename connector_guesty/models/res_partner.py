# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from .guesty_sdk.models import Guest

_log = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    guesty_ids = fields.One2many("res.partner.guesty", "partner_id")

    def write(self, vals):
        rs = super().write(vals)
        if "name" in vals or "email" in vals:
            backend = self.has_guesty_backend()
            if backend:
                guesty_payload = self.guesty_build_payload()
                self.with_delay().guesty_push_update_guest(
                    guesty_payload, backend=backend
                )
        return rs

    def guesty_build_payload(self):
        return {"fullName": self.name, "email": self.email}

    def guesty_push_update_guest(self, payload, backend=None):
        # what is the backend to publish?
        guesty_partner = self.guesty_ids.filtered(
            lambda s: s.guesty_account_id
            and s.guesty_account_id == backend.guesty_account_id
        )

        guesty_partner = self.env["res.partner.guesty"].search(
            [("id", "in", guesty_partner.ids)], limit=1
        )

        if not guesty_partner:
            raise ValidationError(_("Unable to find partner"))
        success, rs = backend.call_put_request(
            url_path="guests/{}".format(guesty_partner.guesty_id), body=payload
        )

        _log.info(rs)

    def has_guesty_backend(self):
        _backend = self.guesty_ids.filtered(
            lambda s: s.is_guesty_default
        ).guesty_get_backend_single()
        if _backend:
            return _backend

        _backend = self.guesty_ids.guesty_get_backend_single()
        if _backend:
            return _backend

        return self.env["backend.guesty"]

    def open_guesty_url(self):
        backend = self.has_guesty_backend()
        if backend:
            guesty_partner = self.guesty_ids.filtered(
                lambda s: s.guesty_account_id
                and s.guesty_account_id == backend.guesty_account_id
            )
            return {
                "name": _("Guesty: Guest"),
                "type": "ir.actions.act_url",
                "url": "https://app-sandbox.guesty.com/contact/guest/{}".format(
                    guesty_partner.guesty_id
                ),
                "target": "new",
            }

    def sync_guesty_accounts(self):
        _backend = self.env.company.guesty_backend_id
        if not _backend:
            return

        _api = _backend.guesty_get_api()
        success, guests = _api.get(Guest).search_by_email(self.email)
        if success:
            for _guest in guests:
                _partner = self.env["res.partner.guesty"].search(
                    [
                        ("partner_id", "=", self.id),
                        ("guesty_id", "=", _guest["_id"]),
                        ("guesty_account_id", "=", _backend.guesty_account_id),
                    ]
                )
                if not _partner:
                    self.env["res.partner.guesty"].create(
                        {
                            "partner_id": self.id,
                            "guesty_id": _guest["_id"],
                            "guesty_account_id": _backend.guesty_account_id,
                            "guesty_name": _guest["fullName"],
                        }
                    )

    def search_by_email(self, email=None):
        if not email:
            return None

        partner_id = self.search([("email", "=", email)], limit=1)

        return partner_id

    def guesty_search_by_email(self):
        pass

    def guesty_push_guest(self, backend, search_by_email=False):
        if search_by_email:
            success, guest_list = (
                backend.guesty_get_api().get(Guest).search_by_email(self.email)
            )
            if success:
                if len(guest_list) > 0:
                    return self.env["res.partner.guesty"].create(
                        {
                            "partner_id": self.id,
                            "guesty_id": guest_list[0]["_id"],
                            "guesty_account_id": backend.guesty_account_id,
                            "guesty_name": guest_list[0]["fullName"],
                        }
                    )

        payload = self.guesty_build_payload()
        success, res = backend.call_post_request(url_path="guests", body=payload)
        if not success:
            raise ValidationError(_("Unable to push guest info"))

        return self.env["res.partner.guesty"].create(
            {
                "partner_id": self.id,
                "guesty_id": res["_id"],
                "guesty_account_id": backend.guesty_account_id,
                "guesty_name": res["fullName"],
            }
        )
