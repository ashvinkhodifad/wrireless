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
        API_KEY = http.request.env['ir.config_parameter'].sudo().get_param('odoo_cenit.wireless.shipstation_api_key')
        API_SECRET = http.request.env['ir.config_parameter'].sudo().get_param('odoo_cenit.wireless.shipstation_api_secret')
        response = requests.get(data.get('resource_url'), auth=(API_KEY, API_SECRET))
        ss_data = json.loads(response.content)

        for shipment in ss_data.get('shipments'):
            oN = shipment.get('orderNumber', '')
            sC = shipment.get('serviceCode', '')
            tN = shipment.get('trackingNumber', '')

            stock_picking = http.request.env['stock.picking'].sudo().search([('origin', '=', oN)], limit=1)

            _logger.info('Stock Picking %s' % stock_picking.name)

            if stock_picking :

                carrier = http.request.env['cenit.wireless.carrier'].sudo().search([('shipstation_servicecode', '=', sC)], limit=1)

                if not carrier:
                    carrier = http.request.env['cenit.wireless.carrier'].sudo().search([], limit=1)

                _logger.info('Carrier %s' % carrier.shipstation_servicecode)

                stock_picking.sudo().write({'carrier_tracking_ref': tN, 'carrier_id': carrier.odoo_carrier.id})

                #action = stock_picking.sudo().button_validate()

                #Validating the stock picking this is the code that appear in process method of stock.immediate.transfer
                process_ptr = True

                try:
                    if stock_picking.state == 'draft':
                        stock_picking.sudo().action_confirm()
                        if stock_picking.state != 'assigned':
                            stock_picking.sudo().action_assign()
                            if stock_picking.state != 'assigned':
                                process_ptr = False
                    if process_ptr:
                        for move in stock_picking.move_lines.sudo().filtered(lambda m: m.state not in ['done', 'cancel']):
                            for move_line in move.move_line_ids:
                                move_line.qty_done = move_line.product_uom_qty
                        stock_picking.sudo().action_done()
                except Exception:
                    pass

                order = http.request.env['sale.order'].sudo().search([('name', '=', oN)], limit=1)

                for orderline in order.order_line:
                    orderline.sudo().write({'bm_state': 3})
                # order.order_line.sudo().write({'bm_state': 3})
            else:
                _logger.info('The stock_picking was NOT found')
                #return {'success': False, 'message': "Stock Picking doesn't exists"}

        return {'success': True, 'message': 'Order Update Process Finished'}


    @http.route('/cenit_wireless/manage_orderline/', auth='public')
    def manage_orderline(self):
        pass