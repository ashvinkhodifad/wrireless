# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Stamps Shipping Service",
    'version': '0.0.1',
    'summary': 'Stamps shipping module to track and place order',
    'author': 'DRC Systems India Pvt. Ltd.',
    'website': 'http://www.drcsystems.com/',
    'description': "Send your shippings through Stamps and track them online",
    'category': 'Warehouse',
    'depends': ['delivery', 'mail','base'],
    'data': [
        'views/delivery_stamps_view.xml',
        'views/res_partner_view.xml',
    ],
    'images': ['static/description/icon.png'],
    'currency': 'EUR',
    'price':55,
    'support':'support@drcsystems.com',
}
