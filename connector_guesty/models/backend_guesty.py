# -*- coding: utf-8 -*-

from odoo import models, fields, api

GUESTY_BASE_URL = "https://api.guesty.com/api/v2/"


class BackendGuesty(models.Model):
    _name = "backend.guesty"

    name = fields.Char(required=True)
    api_key = fields.Char(required=True)
    api_secret = fields.Char(required=True)

    def check_credentials(self):
        pass
