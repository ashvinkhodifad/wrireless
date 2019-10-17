# -*- coding: utf-8 -*-
import base64

import requests
from odoo import http
import json

class CenitWireless(http.Controller):

    @http.route(['/cenit_wireless/manage_order/'], auth='none', methods=['POST'], type='json', csrf=False)
    def manage_order(self):

        data = json.loads(http.request.httprequest.data)
        API_KEY = http.request.env['ir.config_parameter'].sudo().get_param('odoo_cenit.shipstation.key')
        #encode_key = base64.b64encode(bytes(API_KEY, 'utf-8'))
        API_SECRET = http.request.env['ir.config_parameter'].sudo().get_param('odoo_cenit.shipstation.secret')
        #encode_secret = base64.b64encode(bytes(API_SECRET, 'utf-8'))
        response = requests.get(data.get('resource_url'), auth=(API_KEY, API_SECRET))
        ss_data = json.loads(response.content)

        oN = ss_data.get('shipments', [{}])[0].get('orderNumber', '')
        sC = ss_data.get('shipments', [{}])[0].get('serviceCode', '')
        tN = ss_data.get('shipments', [{}])[0].get('trackingNumber', '')

        stock_picking = http.request.env['stock.picking'].search([('origin', '=', oN)], limit=1)

        if stock_picking :
            carrier = http.request.env['cenit.wireless.carrier'].search([('shipstation_servicecode', '=', sC)], limit=1)

            if not carrier:
                carrier = http.request.env['cenit.wireless.carrier'].search([], limit=1)

            stock_picking.write({'carrier_tracking_ref': tN, 'carrier_id': carrier.odoo_carrier.id})

            order = http.request.env['sale.order'].search(['name', '=', oN], limit=1)

            for orderline in order.order_line:
                orderline.bm_state = 3
        else:
            #We should send a message telling the owner the stock.picking doesn't exists
            return {'success': False, 'message': "Stock Picking doesn't exists"}

        return {'success': True, 'message': 'Stock Picking updated'}


    @http.route('/cenit_wireless/manage_orderline/', auth='public')
    def manage_orderline(self):
        return "Hello, world"