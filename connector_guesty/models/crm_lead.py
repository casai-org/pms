# Copyright (C) 2021 Casai (https://www.casai.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
import re
import uuid

import html2text

from odoo import _, fields, models
from odoo.exceptions import ValidationError

_log = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def _check_value(self):
        if self.bed_number > 6 or self.bed_number < 0:
            raise ValidationError(_('Enter Value Between 0-.'))

    check_in = fields.Date()
    check_out = fields.Date()
    state_filter = fields.Many2one('res.country.state', string="City")
    neighborhood = fields.Char(string="Neighborhood")
    bed_number = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'),
                                   ('5', '5'), ('6', '6')], string="Number of Bedrooms", default="")
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
                break
            value_list = re.findall(
                expression_id.expression_string, body_data, flags=re.MULTILINE
            )
            for value in value_list:
                custom_values[expression_id.lead_field] = str(value).strip()
                break

        if "email_from" not in custom_values:
            custom_values["email_from"] = "{}@odoo.casai.com".format(
                uuid.uuid4().hex[:13]
            )

        lead = super().message_new(msg_dict, custom_values=custom_values)
        return lead

    def search_availability(self):

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
        listing_ids = [a.get("listing_id")for a in res]
        #property_list = (
         #   self.env["pms.property"].sudo().search([("guesty_id", "in", listing_ids)])
        #)
        property_domain = [("guesty_id", "in", listing_ids)]
        if self.bed_number and self.neighborhood and self.state_filter:
            property_domain.append(("state_id", "=", self.state_filter.id))
            property_domain.append(("l10n_mx_edi_colony", "=", self.neighborhood))
            property_domain.append(("qty_bedroom", ">=", int(self.bed_number)))
        if self.state_filter and self.neighborhood:
            property_domain.append(("state_id", "=", self.state_filter.id))
            property_domain.append(("l10n_mx_edi_colony", "=", self.neighborhood))
        if self.state_filter and self.bed_number:
            property_domain.append(("state_id", "=", self.state_filter.id))
            property_domain.append(("qty_bedroom", ">=", int(self.bed_number)))
        if self.neighborhood and self.bed_number:
            property_domain.append(("l10n_mx_edi_colony", "=", self.neighborhood))
            property_domain.append(("qty_bedroom", ">=", int(self.bed_number)))
        if self.state_filter:
            property_domain.append(("state_id", "=", self.state_filter.id))
        if self.neighborhood:
            property_domain.append(("l10n_mx_edi_colony", "=", self.neighborhood))
        if self.bed_number:
            property_domain.append(("qty_bedroom", ">=", int(self.bed_number)))

        property_list = self.env["pms.property"].search(property_domain)
        _log.info(property_list)

        backend = self.env.company.guesty_backend_id
        calendar = backend.guesty_get_calendar_info(
            self.check_in, self.check_out, property_list
        )
        _log.info(calendar)

        self.pms_available_listing_ids.sudo().unlink()
        self.sudo().pms_available_listing_ids = [
            (
                0,
                False,
                {
                    "property_id": a.id,
                    "currency": calendar[a.guesty_id]["currency"],
                    "price": calendar[a.guesty_id]["price"],
                },
            )
            for a in property_list
        ]
