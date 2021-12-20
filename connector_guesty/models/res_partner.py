# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    guesty_ids = fields.One2many("res.partner.guesty", "partner_id")
