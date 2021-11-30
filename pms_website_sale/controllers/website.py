# Copyright (c) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import http
from odoo.http import request

from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSale(WebsiteSale):
    def _get_property_search_domain(self):
        return [('property_child_ids', '=', False)]

    def _get_pricelist_context(self):
        pricelist_context = dict(request.env.context)
        pricelist = False
        if not pricelist_context.get("pricelist"):
            pricelist = request.website.get_current_pricelist()
            pricelist_context["pricelist"] = pricelist.id
        else:
            pricelist = request.env["product.pricelist"].browse(
                pricelist_context["pricelist"]
            )

        return pricelist_context, pricelist

    @http.route(
        [
            """/property""",
            """/property/page/<int:page>""",
        ],
        type="http",
        auth="public",
        website=True,
    )
    def property(self, page=0, ppg=False, **post):
        if ppg:
            try:
                ppg = int(ppg)
                post["ppg"] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = request.env["website"].get_current_website().shop_ppg or 20

        ppr = request.env["website"].get_current_website().shop_ppr or 4

        domain = self._get_property_search_domain()

        keep = QueryURL("/property")

        pricelist_context, pricelist = self._get_pricelist_context()

        request.context = dict(
            request.context, pricelist=pricelist.id, partner=request.env.user.partner_id
        )

        Property = request.env["pms.property"].with_context(bin_size=True)

        search_property = Property.search(domain, order="name asc")
        url = "/property"
        product_count = len(search_property)
        pager = request.website.pager(
            url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post
        )
        offset = pager["offset"]
        properties = search_property[offset : offset + ppg]

        layout_mode = "grid"

        values = {
            "pager": pager,
            "pricelist": pricelist,
            "properties": properties,
            "search_count": product_count,  # common for all searchbox
            "bins": properties,
            "ppg": ppg,
            "ppr": ppr,
            "keep": keep,
            "layout_mode": layout_mode,
        }
        return request.render("pms_website_sale.properties", values)
