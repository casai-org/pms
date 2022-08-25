# Copyright (c) 2022 Casai
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo import models, fields, api, tools


class CalendarReport(models.Model):
    _name = "guesty.calendar.report"
    _auto = False

    listing_id = fields.Char()
    state = fields.Char()
    start_date = fields.Date()
    end_date = fields.Date()

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.listing_id} - {rec.state} - CO: {rec.end_date}"

    def init(self):
        tools.drop_view_if_exists(self._cr, 'guesty_calendar_report')
        query = """
            CREATE or REPLACE VIEW guesty_calendar_report AS (
                select min(id) as id, listing_id, state, count(*) as "count", min(listing_date) as start_date, max(listing_date) as end_date from (
                select id, listing_id, state, listing_date, date(listing_date) - row_number() over (partition by listing_id, state order by date(listing_date)) * interval '1 day' "filter"
                from pms_guesty_calendar pgc 
                ) t1 
                group by listing_id, state, filter
                order by listing_id, min(listing_date)
            )
        """

        self._cr.execute(query)
