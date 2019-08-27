# -*- coding: utf-8 -*-
from odoo import http

# class CenitWireless(http.Controller):
#     @http.route('/cenit_wireless/cenit_wireless/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cenit_wireless/cenit_wireless/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cenit_wireless.listing', {
#             'root': '/cenit_wireless/cenit_wireless',
#             'objects': http.request.env['cenit_wireless.cenit_wireless'].search([]),
#         })

#     @http.route('/cenit_wireless/cenit_wireless/objects/<model("cenit_wireless.cenit_wireless"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cenit_wireless.object', {
#             'object': obj
#         })