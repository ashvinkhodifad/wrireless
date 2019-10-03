# -*- coding: utf-8 -*-
import base64

import requests
from odoo import http
import json

class CenitWireless(http.Controller):

    @http.route(['/cenit_wireless/manage_order/'], auth='none', methods=['POST'], type='json', csrf=False)
    def manage_order(self):

        data = json.loads(http.request.httprequest.data)
        API_KEY = '01c7b0b2a5294d4697ed1e587f83fb73'
        API_SECRET = '747da7fefb1c4c54bdfaf7015a5f07e1'
        auth = base64.b64encode(b'01c7b0b2a5294d4697ed1e587f83fb73:747da7fefb1c4c54bdfaf7015a5f07e1')
        response = requests.get(data.get('resource_url'), auth=(API_KEY, API_SECRET))
        ss_data = json.loads(response.data)

        stock_picking = self.env['stock.picking'].search(
            [('origin', '=', ss_data.get('shipments')[0].get('orderNumber'))], limit=1).write(
            {'trackingNumber': ss_data.get('shipments')[0].get('orderNumber'),
             'servicesCode': ss_data.get('shipments')[0].get('serviceCode')})
        return {'success': True}


    @http.route('/cenit_wireless/manage_orderline/', auth='public')
    def manage_orderline(self, **kw):
        print(http.request)
        return "Hello, world"