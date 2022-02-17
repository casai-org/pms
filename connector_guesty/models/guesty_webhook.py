# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .guesty_sdk.models import Webhook

_log = logging.getLogger(__name__)


class GuestyWebhookEvent(models.Model):
    _name = "backend.guesty.webhook.event"

    name = fields.Char()
    event_name = fields.Char()


class GuestyWebhook(models.Model):
    _name = "backend.guesty.webhook"

    backend_id = fields.Many2one("backend.guesty")
    name = fields.Char()
    event_ids = fields.Many2many("backend.guesty.webhook.event")
    event_url = fields.Char()

    guesty_id = fields.Char()

    @api.model
    def create(self, vals_list):
        rs = super().create(vals_list)
        assert isinstance(rs, GuestyWebhook)

        _log.info(rs)
        _log.info(rs.event_url)

        guesty_api = rs.backend_id.guesty_get_api()
        success, webhook = guesty_api.get(Webhook).create(
            url=rs.event_url,
            account_id=rs.backend_id.guesty_account_id,
            events=[ev.event_name for ev in rs.event_ids],
        )
        if success:
            rs.write({"guesty_id": webhook["_id"]})
        return rs

    def unlink(self):
        for record in self:
            if not record.guesty_id:
                continue

            guesty_api = record.backend_id.guesty_get_api()
            success, result = guesty_api.get(Webhook).delete(uuid=record.guesty_id)
            if not success:
                raise UserError(_("Unable to delete record: {}".format(result)))
        return super().unlink()
