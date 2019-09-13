# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2010, 2014 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging, os

from odoo import models, fields, api, _


_logger = logging.getLogger(__name__)

class CenitWirelessSettings(models.TransientModel):
    _name = "cenit.wireless.settings"
    _inherit = 'res.config.settings'

    ############################################################################
    # Pull Parameters
    ############################################################################
    email = fields.Char('Email for notifications')
    enabled_err_msg = fields.Boolean(string=_('Enable error messages'), default=True)
    enable_sync_msg = fields.Boolean(string=_('Enable sync events messages'), default=False)

    ############################################################################
    # Default Getters
    ############################################################################
    def get_values_email(self):
        email = self.env['ir.config_parameter'].get_param(
            'odoo_cenit.wireless.email', default=None
        )
        return {'key': email or ''}

    def get_values_errmsg(self):
        err_msg = self.env['ir.config_parameter'].get_param(
            'odoo_cenit.wireless.errmsg', default=None
        )
        return {'secret': err_msg or ''}

    def get_values_syncmsg(self):
        sync_msg = self.env['ir.config_parameter'].get_param(
            'odoo_cenit.wireless.syncmsg', default=None
        )
        return {'store_id': sync_msg or ''}

    ############################################################################
    # Default Setters
    ############################################################################
    def set_values(self):
        config_parameters = self.env['ir.config_parameter']
        for record in self.browse(self.ids):
            config_parameters.set_param(
                'odoo_cenit.wireless.email', record.email or ''
            )

        for record in self.browse(self.ids):
            config_parameters.set_param(
                'odoo_cenit.wireless.errmsg', record.enabled_err_msg or ''
            )

        for record in self.browse(self.ids):
            config_parameters.set_param(
                'odoo_cenit.wireless.syncmsg', record.enable_sync_msg or ''
            )