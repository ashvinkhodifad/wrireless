# -*- encoding: utf-8 -*-
{
    'name': 'Arion Wireless Stock',
    'version': '0.1',
    'summary': 'Arion Wireless: Stock',
    'description': """
Arion Wireless: Stock
=====================
* [2034194]
    - Assign Serial number on detail operation using Button for Incoming Picking
    - print label of the products with the following information:
        - product display name
        - internal reference field (SKU) displayed as a scannable barcode
* [2035782]
    - Availability of kit products qty
    """,
    'category': 'Custom Dev',
    'website': 'http://odoo.com',
    'depends': ['stock', 'mrp'],
    'data': [
        # data
        'data/paperformat_data.xml',
        'data/sequence_data.xml',

        # views
        # 'views/product_view.xml',
        'views/stock_view.xml',

        # report
        'report/stock_picking_label_report.xml',
    ],
    'demo': [],

    'installable': True,
    'application': False,
    'auto_install': False,
}
