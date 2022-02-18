# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import datetime
import logging
import re
import uuid

import html2text

from odoo import _, fields, models
from odoo.exceptions import ValidationError

_log = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    check_in = fields.Date()
    check_out = fields.Date()
    pms_available_listing_ids = fields.One2many("pms.available.listing", "lead_id")

    def message_new(self, msg_dict, custom_values=None):
        # add a custom behavior when receiving a new lead through the mail's gateway
        custom_values = custom_values or {}
        if custom_values.get("type", "not_defined") not in ["lead", "opportunity"]:
            return super().message_new(msg_dict, custom_values=custom_values)

        body_data = msg_dict.get("body", str())
        body_data = html2text.html2text(body_data)
        expression_ids = self.env["crm.lead.rule"].sudo().search([])
        for expression_id in expression_ids:
            _log.info(expression_id.expression_string)
            if expression_id.lead_field in custom_values:
                continue
            value_list = re.findall(
                expression_id.expression_string, body_data, flags=re.MULTILINE
            )
            for value in value_list:
                _log.info(value)
                custom_values[expression_id.lead_field] = str(value).strip()
                break

        if "email_from" not in custom_values:
            if msg_dict.get("email_from"):
                _email_ = msg_dict["email_from"]
                lst_mail = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", _email_)
                if lst_mail:
                    _email_ = lst_mail.group(0)

                # Todo(jorge.juarez@casai.com): found a way to have a black list
                if _email_ and (
                    "casai.com" not in _email_ and "casai.zendesk.com" not in _email_
                ):
                    custom_values["email_from"] = _email_

        if "email_from" not in custom_values:
            custom_values["email_from"] = "{}@odoo.casai.com".format(
                uuid.uuid4().hex[:13]
            )

        lead = super().message_new(msg_dict, custom_values=custom_values)
        return lead

    def search_availability(self):
        if not self.check_in or not self.check_out:
            raise ValidationError(_("Please fill the required fields"))
        query = """
        select *
        from (
                 select count(*) as no_states,
                        t.listing_id,
                        t.first_state
                 from (
                          select calendar.state,
                                 calendar.listing_id,
                                 first_value(calendar.state) over (order by calendar.state)
                                 as first_state
                          from pms_guesty_calendar calendar
                          where calendar.listing_date between '{}' and '{}'
                          group by calendar.listing_id, calendar.state
                      ) as t
                 group by t.listing_id, t.first_state
             ) as t_final
        where (
              t_final.no_states = 1
          and t_final.first_state = 'available'
        )
        """.format(
            self.check_in, self.check_out
        )

        self.env.cr.execute(query)
        res = self.env.cr.dictfetchall()
        listing_ids = [a.get("listing_id") for a in res]
        property_list = (
            self.env["pms.property"].sudo().search([("guesty_id", "in", listing_ids)])
        )

        backend = self.env.company.guesty_backend_id
        real_checkout = self.check_out - datetime.timedelta(days=1)

        calendar = backend.guesty_get_calendar_info(
            self.check_in, real_checkout, property_list
        )

        # _log.info()

        self.pms_available_listing_ids.sudo().unlink()
        self.sudo().pms_available_listing_ids = [
            (
                0,
                False,
                {
                    "property_id": a.id,
                    "currency": calendar[a.guesty_id]["currency"],
                    "price": calendar[a.guesty_id]["price"],
                    "no_nights": calendar[a.guesty_id]["no_nights"],
                    "check_in": self.check_in,
                    "check_out": self.check_out,
                },
            )
            for a in property_list
        ]

        return {
            "type": "ir.actions.act_window",
            "name": _(
                "Quoting reservation: ({} - {})".format(self.check_in, self.check_out)
            ),
            "res_model": "pms.available.listing",
            "domain": [["id", "in", self.pms_available_listing_ids.ids]],
            "views": [[False, "tree"]],
            # "target": "new"
        }
