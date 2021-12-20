# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartnerGuesty(models.Model):
    _name = "res.partner.guesty"

    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    guesty_id = fields.Char(required=True)
