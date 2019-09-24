# -*- coding: utf-8 -*-
from odoo import http

class CenitWireless(http.Controller):

    @http.route(['/cenit_wireless/manage_order/'], auth='none', methods=['POST'], type='json', csrf=False)
    def manage_order(self, **kw):
        tmp1 = http.request.keys()
        tmp2 = kw.keys()
        return {'success': True}


    @http.route('/cenit_wireless/manage_orderline/', auth='public')
    def manage_orderline(self, **kw):
        print(http.request)
        return "Hello, world"