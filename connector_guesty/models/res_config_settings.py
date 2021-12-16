# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = "res.company"

    guesty_backend_id = fields.Many2one("backend.guesty")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    guesty_backend_id = fields.Many2one("backend.guesty", string="Guesty backend connector")

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env.company.guesty_backend_id = self.guesty_backend_id.id
        return res

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(guesty_backend_id=self.env.company.guesty_backend_id)
        return res
