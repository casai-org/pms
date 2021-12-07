# Copyright (c) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import http
from odoo.http import request

from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website_sale.controllers.main import WebsiteSale


class PropertyTableCompute(object):
    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey, ppr):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx + x >= ppr:
                    res = False
                    break
                row = self.table.setdefault(posy + y, {})
                if row.setdefault(posx + x) is not None:
                    res = False
                    break
            for x in range(ppr):
                self.table[posy + y].setdefault(x, None)
        return res

    def process(self, products, ppg=20, ppr=4):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        x = 0
        for p in products:
            x = min(1, ppr)
            y = min(1, ppr)
            if index >= ppg:
                x = y = 1

            pos = minpos
            while not self._check_place(pos % ppr, pos // ppr, x, y, ppr):
                pos += 1
            # if 21st products (index 20) and the last line is full (ppr products in it), break
            # (pos + 1.0) / ppr is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= ppg and ((pos + 1.0) // ppr) > maxy:
                break

            if x == 1 and y == 1:  # simple heuristic for CPU optimization
                minpos = pos // ppr

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos // ppr) + y2][(pos % ppr) + x2] = False
            self.table[pos // ppr][pos % ppr] = {"product": p, "x": x, "y": y}
            if index <= ppg:
                maxy = max(maxy, y + (pos // ppr))
            index += 1

        # Format table according to HTML needs
        rows = sorted(self.table.items())
        rows = [r[1] for r in rows]
        for col in range(len(rows)):
            cols = sorted(rows[col].items())
            x += len(cols)
            rows[col] = [r[1] for r in cols if r[1]]

        return rows


class WebsiteSale(WebsiteSale):
    def _get_property_search_domain(self, search, amenity, guest):
        domain = []
        if search:
            domain += [("city", "ilike", search)]
        if amenity:
            domain += [("amenity_ids.name", "ilike", amenity)]
        if guest:
            domain += [("no_of_guests", ">=", int(guest))]
        domain += [("property_child_ids", "=", False)]
        return domain

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
        ["""/property""", """/property/page/<int:page>"""],
        type="http",
        auth="public",
        website=True,
    )
    def property(self, page=0, ppg=False, search="", amenity="", guest="", **post):
        if ppg:
            try:
                ppg = int(ppg)
                post["ppg"] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = request.env["website"].get_current_website().shop_ppg or 20

        ppr = request.env["website"].get_current_website().shop_ppr or 4

        domain = self._get_property_search_domain(
            search=search, amenity=amenity, guest=guest
        )

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
        # properties
        values = {
            "search": search,
            "amenity": amenity,
            "guest": guest,
            "pager": pager,
            "pricelist": pricelist,
            "properties": properties,
            "search_count": product_count,  # common for all searchbox
            "bins": PropertyTableCompute().process(properties, ppg, ppr),
            "ppg": ppg,
            "ppr": ppr,
            "keep": keep,
            "layout_mode": layout_mode,
        }
        return request.render("pms_website_sale.properties", values)
