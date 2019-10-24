# -*- coding: utf-8 -*-

import requests
from odoo import http
import json

import logging
_logger = logging.getLogger(__name__)

class CenitWireless(http.Controller):

    @http.route(['/cenit_wireless/manage_order/'], auth='none', methods=['POST'], type='json', csrf=False)
    def manage_order(self):

        _logger.info('The webhook is called successfuly')

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

        _logger.info('The orderNumber is %s' % oN)
        _logger.info('The serviceCode is %s' % sC)
        _logger.info('The trackingNumber is %s' % tN)

        stock_picking = http.request.env['stock.picking'].sudo().search([('origin', '=', 'BM197123')], limit=1)

        if stock_picking :
            _logger.info('The stock_picking was found')

            carrier = http.request.env['cenit.wireless.carrier'].sudo().search([('shipstation_servicecode', '=', sC)], limit=1)

            if not carrier:
                carrier = http.request.env['cenit.wireless.carrier'].sudo().search([], limit=1)

            stock_picking.sudo().write({'carrier_tracking_ref': tN, 'carrier_id': carrier.odoo_carrier.id})

            order = http.request.env['sale.order'].sudo().search(['name', '=', oN], limit=1)

            for orderline in order.order_line:
                orderline.sudo().write({'bm_state': 3})

            # order.order_line.sudo().write({'bm_state': 3})

        else:
            #We should send a message telling the owner the stock.picking doesn't exists
            _logger.info('The stock_picking was not found')
            return {'success': False, 'message': "Stock Picking doesn't exists"}

        return {'success': True, 'message': 'Stock Picking updated'}


    @http.route('/cenit_wireless/manage_orderline/', auth='public')
    def manage_orderline(self):

        return "Hello, world"