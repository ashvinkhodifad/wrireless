# -*- coding: utf-8 -*-
{
     # App information
    'name': 'Helpdesk Extension',
    'version': '12.0',
    'category': 'Hidden/Dependency',
    'summary': '',
    'license': 'OPL-1',
    
    # Dependencies
    
    'depends': ['helpdesk', 'sale_management'],
    
     # Views
    
    'data': [
        'view/helpdesk_ept.xml',
        'view/sale_order_view.xml'
    ],
    
     
    # Odoo Store Specific
    
    'images': ['static/description/Helpdesk-extension-cover.jpg'],
    
     # Author

    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',
    
    
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': '10',
    'currency': 'EUR',
}
