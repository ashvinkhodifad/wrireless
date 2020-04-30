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

    bm_url = fields.Char(string=_('Backmarket URL'))
    bm_token = fields.Char(string=_('Backmarket Authentication Token'), required=True)
    bm_user_agent = fields.Char(string=_('Backmarket User Agent'))

    shipstation_api_key = fields.Char('Shipstation API Key', required=True)
    shipstation_api_secret = fields.Char('Shipstation API Secret', required=True)
    shipstation_store = fields.Char('Shipstation Store')

    _3pl_client_id = fields.Char('3PL Client ID', required=True)
    _3pl_client_secret = fields.Char('3PL Client Secret', required=True)
    _3pl_costumer_id = fields.Char('3PL Customer ID', required=True)
    _3pl_facility_id = fields.Char('3PL Facility ID', required=True)
    _3pl_tpl_guid = fields.Char('3PL TPL GUID', required=True)
    _3pl_userlogin_id = fields.Char('3PL UserLogin ID', required=True)


    ############################################################################
    # Default Getters
    ############################################################################
    # def get_values_email(self):
    #     email = self.env['ir.config_parameter'].get_param(
    #         'odoo_cenit.wireless.email', default=None
    #     )
    #     return {'key': email or ''}
    #
    # def get_values_errmsg(self):
    #     err_msg = self.env['ir.config_parameter'].get_param(
    #         'odoo_cenit.wireless.errmsg', default=None
    #     )
    #     return {'secret': err_msg or ''}
    #
    # def get_values_syncmsg(self):
    #     sync_msg = self.env['ir.config_parameter'].get_param(
    #         'odoo_cenit.wireless.syncmsg', default=None
    #     )
    #     return {'store_id': sync_msg or ''}
    #

    @api.model
    def get_values(self):
        res = super(CenitWirelessSettings, self).get_values()
        res.update(
            email=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless.email", default=None),
            enabled_err_msg=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless.errmsg", default=None),
            enable_sync_msg=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless.syncmsg", default=None),
            bm_url=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless.bm_url", default=None),
            bm_token = self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless.bm_token", default=None),
            bm_user_agent = self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless.bm_user_agent", default=None),
            shipstation_api_key=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless.shipstation_api_key", default=None),
            shipstation_api_secret=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless.shipstation_api_secret", default=None),
            shipstation_store=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless.shipstation_store", default=None),
            _3pl_client_id=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless._3pl_client_id", default=None),
            _3pl_client_secret=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless._3pl_client_secret", default=None),
            _3pl_costumer_id=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless._3pl_costumer_id", default=None),
            _3pl_facility_id=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless._3pl_facility_id", default=None),
            _3pl_tpl_guid=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless._3pl_tpl_guid", default=None),
            _3pl_userlogin_id=self.env["ir.config_parameter"].sudo().get_param("odoo_cenit.wireless._3pl_userlogin_id", default=None)

        )
        return res

    ############################################################################
    # Default Setters
    ############################################################################
    # def set_values(self):
    #     config_parameters = self.env['ir.config_parameter']
    #     for record in self.browse(self.ids):
    #         config_parameters.set_param(
    #             'odoo_cenit.wireless.email', record.email or ''
    #         )
    #
    #     for record in self.browse(self.ids):
    #         config_parameters.set_param(
    #             'odoo_cenit.wireless.errmsg', record.enabled_err_msg or ''
    #         )
    #
    #     for record in self.browse(self.ids):
    #         config_parameters.set_param(
    #             'odoo_cenit.wireless.syncmsg', record.enable_sync_msg or ''
    #         )

    def set_values(self):
        super(CenitWirelessSettings, self).set_values()
        for record in self:
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless.email", record.email or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless.errmsg", record.enabled_err_msg or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless.syncmsg", record.enable_sync_msg or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless.bm_url", record.bm_url or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless.bm_token", record.bm_token or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless.bm_user_agent", record.bm_user_agent or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless.shipstation_api_key", record.shipstation_api_key or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless.shipstation_api_secret", record.shipstation_api_secret or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless.shipstation_store", record.shipstation_store or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless._3pl_client_id", record._3pl_client_id or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless._3pl_client_secret", record._3pl_client_secret or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless._3pl_costumer_id", record._3pl_costumer_id or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless._3pl_facility_id", record._3pl_facility_id or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless._3pl_tpl_guid", record._3pl_tpl_guid or '')
            self.env['ir.config_parameter'].sudo().set_param("odoo_cenit.wireless._3pl_userlogin_id", record._3pl_userlogin_id or '')



class CenitWirelessCarrier(models.Model):
    _name = "cenit.wireless.carrier"

    _rec_name = 'shipstation_servicecode'

    shipstation_servicecode = fields.Char(string=_('Shipstation Carrier Code'))
    odoo_carrier = fields.Many2one('delivery.carrier', string=_("Internal Delivery Carrier"))


class CenitWirelessCarrierProduct(models.Model):
    _name = "cenit.wireless.carrier.product"

    _rec_name = 'odoo_carrier'

    odoo_carrier = fields.Many2one('delivery.carrier', string=_("Odoo Shipping Method"))
    product = fields.Many2one('product.product', string=_("Shipping Service as Product"))

