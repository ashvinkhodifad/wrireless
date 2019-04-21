# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    apo_fpo_dpo = fields.Boolean(string="Is APO/FPO/DPO?", default=False, help="Select if the address in Military base or Diplomatic location.")
    zip_code_addon = fields.Char(string="ZIP Code addon", size=4, help="The (plus 4) portion of the ZIP Code for this address only used for domestic addresses. Max length 4")
