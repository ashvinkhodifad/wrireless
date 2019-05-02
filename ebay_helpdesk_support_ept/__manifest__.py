# -*- coding: utf-8 -*-pack
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    # App information 
    'name':'eBay Helpdesk',
    'version':'12.0',
    'category': 'Website',
    'summary' :'Creates Helpdesk ticket in Odoo from eBay customer messages.',
    'license': 'OPL-1',
    
    # Dependencies
    'depends':['base','ebay_ept','base_automation','helpdesk_ept'],
    
    # Views
    'data':['view/ebay_helpdesk_support_view.xml'],
    
    # Odoo Store Specific
	'images': ['static/description/eBay-Helpdesk-Cover.jpg'],
	
	# Author 
    "author": "Emipro Technologies Pvt. Ltd.",
    'website': 'http://www.emiprotechnologies.com/',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',
               
               
    'installable': True,
    'auto_install': False,
    'application' : True,
    'live_test_url':'https://www.emiprotechnologies.com/free-trial?app=ebay-helpdesk-suppport-ept&version=12&edition=enterprise',
    'price': '40',
    'currency': 'EUR',
}
