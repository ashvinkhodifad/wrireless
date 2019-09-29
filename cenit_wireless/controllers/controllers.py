# -*- coding: utf-8 -*-
from odoo import http
import json

class CenitWireless(http.Controller):

    @http.route(['/cenit_wireless/manage_order/'], auth='none', methods=['POST'], type='json', csrf=False)
    def manage_order(self):

        data = json.loads(http.request.httprequest.data)
        import requests
        tmp = requests.get(data.get('resource_url'), '')
        return {'success': True}


    @http.route('/cenit_wireless/manage_orderline/', auth='public')
    def manage_orderline(self, **kw):
        print(http.request)
        return "Hello, world"