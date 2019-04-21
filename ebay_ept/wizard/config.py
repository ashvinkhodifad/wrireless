#!/usr/bin/python3
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta

_intervalTypes = {
    'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}

class ebay_instance_config(models.TransientModel):
    _name = 'res.config.ebay.instance'
    _description = "eBay Res Configuration Instance"
    
    name = fields.Char("Instance Name")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    dev_id = fields.Char('Dev ID',size=256,required=True,help="Dev ID")
    app_id = fields.Char('App ID (Client ID)',size=256,required=True,help="App ID")
    cert_id = fields.Char('Cert ID (Client Secret)',size=256,required=True,help="Cert ID")
    server_url = fields.Char('Server URL',size=256,help="eBay Server URL")
    environment = fields.Selection([('is_sandbox', 'Sandbox'),('is_production', 'Production')],'Environment')
    auth_token = fields.Text('Token',help="eBay Token")
    country_id = fields.Many2one('res.country',string = "Country")
    
    fetch_token_boolean = fields.Boolean('GetToken')
    redirect_url_name = fields.Char('eBay Redirect URL Name',size=256,help="eBay Redirect URL Name")
    username = fields.Char('eBay Username',size=256,help="eBay Username")
    password = fields.Char('eBay Password',size=256,help="eBay Password")
    
    #allow user to set product site url for ebay
    product_site_url = fields.Char('Product Site URL',help="Product site URL.")
    
    #Add the Allow Stock Product
    allow_out_of_stock_product = fields.Boolean(string="Allow out of stock ?", help="When the quantity of your Good 'Til Cancelled listing reaches zero, the listing remains active but is hidden from search until you increase the quantity. You may also qualify for certain fee credits",default=True)
    
    @api.onchange('environment')
    def onchange_environment(self): 
        if self.environment == 'is_sandbox':
            self.server_url = 'https://api.sandbox.ebay.com/ws/api.dll'
        else:
            self.server_url = 'https://api.ebay.com/ws/api.dll'
            
    @api.onchange('fetch_token_boolean')
    def onchange_fetch_token_boolean(self):
        if self.fetch_token_boolean :
            self.auth_token = ''
        else:
            self.username = ''
            self.password = ''
            self.redirect_url_name = ''

    @api.multi
    def test_ebay_connection(self):
        self.env['ebay.instance.ept'].create({  
            'name':self.name,
            'dev_id':self.dev_id,                                                 
            'app_id':self.app_id,
            'cert_id':self.cert_id,
            'server_url':self.server_url,
            'environment':self.environment,
            'auth_token': self.auth_token,
            'country_id':self.country_id.id,
            'warehouse_id':self.warehouse_id.id,
            'fetch_token_boolean':self.fetch_token_boolean,
            'redirect_url_name':self.redirect_url_name,
            'username':self.username,
            'password':self.password,
            'allow_out_of_stock_product':self.allow_out_of_stock_product,
            'product_url':'https://www.%s/itm/'%self.product_site_url
        })        
        return True
    
class ebay_config_settings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def create(self, vals):
        if not vals.get('ebay_company_id'):
            vals.update({'ebay_company_id': self.env.user.company_id.id})
        res = super(ebay_config_settings, self).create(vals)
        return res

    ebay_instance_id = fields.Many2one('ebay.instance.ept','Instance',help="Select eBay instance.")
    is_ebay_auto_get_feedback=fields.Boolean(string="eBay Auto Get FeedBacks ?")
    get_ebay_feedback_interval_number = fields.Integer(string='eBay Import Feedback Interval Number',help="Repeat every x.")
    get_ebay_feedback_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], string='eBay Import Feedback Interval Unit')
    get_ebay_feedback_next_execution = fields.Datetime(string='eBay Next Execution of Import Feedback', help='Next execution time')
    get_ebay_feedback_user_id = fields.Many2one('res.users',string="eBay Feedback",help='User')
    
    ebay_warehouse_id = fields.Many2one('stock.warehouse',string="eBay Warehouse")
    ebay_partner_id = fields.Many2one('res.partner', string='eBay Default Customer')
    ebay_country_id = fields.Many2one('res.country',string="Country")
    ebay_lang_id = fields.Many2one('res.lang', string='Language')
    ebay_order_prefix = fields.Char(size=10, string='eBay Order Prefix')
    ebay_price_tax_included = fields.Boolean(string='Is eBay Price Tax Included ?')
    ebay_tax_id = fields.Many2one('account.tax',string='eBay Default Sales Tax')
    
    ebay_fetch_token_boolean = fields.Boolean(string='Fetch eBay Token Boolean',related='ebay_instance_id.fetch_token_boolean', store=False)
    ebay_redirect_url_name = fields.Char(string='RuName',related='ebay_instance_id.redirect_url_name', store=False)

    ebay_order_auto_import = fields.Boolean(string='eBay Auto Order Import ?')
    ebay_order_import_interval_number = fields.Integer(string='eBay Import Order Interval Number',help="Repeat every x.")
    ebay_order_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')],string='eBay Import Order Interval Unit')
    ebay_order_import_next_execution = fields.Datetime(string='eBay Next Execution of Import Order', help='Next execution time')
    is_ebay_import_shipped_order = fields.Boolean(string="eBay Import Shipped Orders ?",default=False,help="Import Shipped Orders.")
    
    ebay_order_auto_update=fields.Boolean(string="eBay Auto Order Update ?")
    ebay_order_update_interval_number = fields.Integer(string='eBay Update Order Interval Number',help="Repeat every x.")
    ebay_order_update_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], string='eBay Update Order Interval Unit')
    ebay_order_update_next_execution = fields.Datetime(string='eBay Next Execution of Update Order', help='Next execution time')
    
    ebay_stock_auto_export=fields.Boolean(string="eBay Auto Inventory Export ?")
    ebay_update_stock_interval_number = fields.Integer(string='eBay Update Stock Interval Number',help="Repeat every x.")
    ebay_update_stock_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'), ('work_days','Work Days'), ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], string='eBay Update Stock Interval Unit')
    ebay_update_stock_next_execution = fields.Datetime(string='eBay Next Execution of Update Stock', help='Next execution time')
        
    ebay_auto_update_payment=fields.Boolean(string="eBay Auto Update Payment On Invoice Paid ?")
    ebay_default_product_category_id = fields.Many2one('product.category',string='eBay Default Product Category')
    ebay_stock_field = fields.Many2one('ir.model.fields', string='Inventory Field')
    ebay_pay_mthd = fields.Selection([('PayPal', 'PayPal'),('PaisaPay', 'PaisaPay')],string='eBay Payment Methods',help="Method of Payment")
    ebay_email_add = fields.Char('Paypal Email ID', size=126,help="Seller paypal email id")
    ebay_site_id = fields.Many2one('ebay.site.details',string='eBay Site')
    ebay_pricelist_id = fields.Many2one('product.pricelist', string='eBay Pricelist')
    ebay_shipment_charge_product_id=fields.Many2one("product.product",string="eBay Shipment Fee",domain=[('type','=','service')])
    ebay_create_new_product=fields.Boolean(string="eBay Auto Create New Product ?",default=False)
    create_quotation_without_product=fields.Boolean("Create Quotation Without Product ?",default=False)
    ebay_fiscal_position_id = fields.Many2one('account.fiscal.position',string='eBay Fiscal Position')
    ebay_team_id=fields.Many2one('crm.team', string='eBay Sales Team',oldname='section_id')
    ebay_post_code = fields.Char(string='eBay Postal Code',size=64,help="Enter the Postal Code for Item Location")
    ebay_company_id=fields.Many2one('res.company',string="eBay Company")
    ebay_discount_charge_product_id=fields.Many2one("product.product",string= "eBay Order Discount",domain=[('type','=','service')])
    ebay_plus=fields.Boolean(string="Is eBay Plus Account ?",default=False)
    ebay_order_import_user_id = fields.Many2one('res.users',string="eBay Import Order By User",help='User')
    ebay_order_status_update_user_id = fields.Many2one('res.users',string="eBay Update Order Status By User",help='User')
    ebay_stock_update_user_id = fields.Many2one('res.users',string="eBay Stock Update By User",help='User')
    ebay_use_dynamic_desc = fields.Boolean(string="eBay Use Dynamic Description Template ?", help='If ticked then you can able to use dynamic product description for an individual product only.')
    
    # Auto sync. active product     
    ebay_auto_sync_active_products = fields.Boolean(string="eBay Auto Sync. Active Products ?",help="Auto Sync. Active Products ?")
    ebay_sync_active_products_interval_number = fields.Integer(string="eBay Auto Sync. Active Products Interval Number",help="Repeat every x.")
    ebay_sync_active_products_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ],string="eBay Auto Sync. Active Products Interval Unit")
    ebay_sync_active_products_next_execution = fields.Datetime(string="eBay Next Execution of Sync. Active Product",help="Next Execution Time")
    ebay_sync_active_products_user_id = fields.Many2one("res.users",string="eBay Sync. Active Products By User",help="User Name")
    ebay_sync_active_products_start_date = fields.Date(string="eBay Sync. Active Products Start Date",help="Sync. Active Products Start Date")
        
    # Auto send invoice mail     
    ebay_auto_send_invoice_via_email = fields.Boolean(string="eBay Auto Send Invoice Via Email ?",help="Auto Send Invoice Via Email.")
    ebay_send_invoice_via_email_interval_number = fields.Integer(string="eBay Auto Send Invoice Via Email Interval Number",help="Repeat every x.")
    ebay_send_invoice_via_email_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('work_days', 'Work Days'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], string="eBay Auto Send Invoice Via Email Interval Unit")
    ebay_send_invoice_via_email_next_execution = fields.Datetime(string="eBay Next Execution of Send Invoice Via Mail", help="Next Execution Time")
    ebay_send_invoice_template_id = fields.Many2one('mail.template', string="eBay Invoice Template")
    ebay_send_invoice_user_id = fields.Many2one("res.users", string="eBay Send Invoice By User", help="User Name")

    # Global channel
    ebay_global_channel_id=fields.Many2one('global.channel.ept' ,string='eBay Global Channel')
    ebay_product_url = fields.Char(string='eBay Product URL')
    ebay_item_location_country = fields.Many2one("res.country",string="eBay Item Location(Country)",help="Select the country for the Item Location.")
    ebay_item_location_name = fields.Char(string="eBay Item Location(City, State) Name",help="Item Location(City, State) name.")

    @api.onchange('ebay_instance_id')
    def onchange_ebay_instance_id(self):
        instance = self.ebay_instance_id
        if instance:
            self.is_ebay_auto_get_feedback = instance.is_auto_get_feedback or False
            self.ebay_price_tax_included = instance.price_tax_included or False
            self.ebay_warehouse_id = instance.warehouse_id and instance.warehouse_id.id or False
            self.ebay_lang_id = instance.lang_id and instance.lang_id.id or False
            self.ebay_order_prefix = instance.order_prefix and instance.order_prefix
            self.ebay_stock_field = instance.stock_field and instance.stock_field.id or False
            self.ebay_pricelist_id = instance.pricelist_id and instance.pricelist_id.id or False         
            self.ebay_fiscal_position_id = instance.fiscal_position_id and instance.fiscal_position_id.id or False
            # Import Order
            self.ebay_order_auto_import = instance.order_auto_import
            self.is_ebay_import_shipped_order = instance.is_import_shipped_order or False
            self.ebay_stock_auto_export = instance.stock_auto_export
            self.ebay_order_auto_update = instance.ebay_order_auto_update
            self.ebay_default_product_category_id = instance.ebay_default_product_category_id and instance.ebay_default_product_category_id.id or False
            self.ebay_pay_mthd = instance.pay_mthd
            self.ebay_email_add = instance.email_add
            self.ebay_site_id = instance.site_id and instance.site_id.id or False
            self.ebay_team_id = instance.team_id and instance.team_id.id or False
            self.ebay_shipment_charge_product_id = instance.shipment_charge_product_id and instance.shipment_charge_product_id.id or False
            self.ebay_post_code = instance.post_code or False
            self.ebay_tax_id = instance.tax_id and instance.tax_id.id or False
            self.ebay_create_new_product = instance.create_new_product or False
            self.ebay_create_quotation_without_product = instance.create_quotation_without_product or False
            self.ebay_company_id = instance.company_id and instance.company_id.id or False
            self.ebay_discount_charge_product_id = instance.discount_charge_product_id and instance.discount_charge_product_id.id or False
            self.ebay_plus = instance.ebay_plus or False
            self.ebay_auto_update_payment = instance.auto_update_payment
            self.ebay_use_dynamic_desc= instance.use_dynamic_desc or False
            self.ebay_auto_send_invoice_via_email = instance.auto_send_invoice_via_email
            self.ebay_send_invoice_template_id = instance.send_invoice_template_id.id or False
            
            self.ebay_auto_sync_active_products = instance.auto_sync_active_products
            self.ebay_sync_active_products_start_date = instance.sync_active_products_start_date
            self.ebay_partner_id = instance.partner_id and instance.partner_id.id or False  
            
            # Global channel
            self.ebay_global_channel_id = instance.global_channel_id and instance.global_channel_id.id or False
            self.ebay_product_url =  instance.product_url or ''
            self.ebay_item_location_country = instance and instance.item_location_country and instance.item_location_country.id or False
            self.ebay_item_location_name = instance and instance.item_location_name or ''

            # Auto Get Feedback
            try:
                get_feedback_cron_exist = self.env.ref('ebay_ept.ir_cron_get_feedback_%d'%(instance.id),raise_if_not_found=False)
            except:
                get_feedback_cron_exist=False
            if get_feedback_cron_exist:
                self.get_ebay_feedback_interval_number = get_feedback_cron_exist.interval_number or False
                self.get_ebay_feedback_interval_type = get_feedback_cron_exist.interval_type or False
                self.get_ebay_feedback_next_execution = get_feedback_cron_exist.nextcall or False
                self.get_ebay_feedback_user_id = get_feedback_cron_exist.user_id.id or False
            
            # Auto Export Inventory
            try:
                inventory_cron_exist = self.env.ref('ebay_ept.ir_cron_auto_export_inventory_instance_%d'%(instance.id),raise_if_not_found=False)
                            
            except:
                inventory_cron_exist=False
            if inventory_cron_exist:
                self.ebay_update_stock_interval_number=inventory_cron_exist.interval_number or False
                self.ebay_update_stock_interval_type=inventory_cron_exist.interval_type or False
                self.ebay_update_stock_next_execution = inventory_cron_exist.nextcall or False
                self.ebay_stock_update_user_id = inventory_cron_exist.user_id.id or False
            
            # Auto Import Order
            try:
                order_import_cron_exist = self.env.ref('ebay_ept.ir_cron_send_ebay_import_sales_orders_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                order_import_cron_exist=False
            if order_import_cron_exist:
                self.ebay_order_import_interval_number = order_import_cron_exist.interval_number or False
                self.ebay_order_import_interval_type = order_import_cron_exist.interval_type or False
                self.ebay_order_import_next_execution = order_import_cron_exist.nextcall or False
                self.ebay_order_import_user_id = order_import_cron_exist.user_id.id or False
            
            # Auto update order status
            try:
                order_update_cron_exist = self.env.ref('ebay_ept.ir_cron_update_order_status_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                order_update_cron_exist=False
            if order_update_cron_exist:
                self.ebay_order_update_interval_number= order_update_cron_exist.interval_number or False
                self.ebay_order_update_interval_type= order_update_cron_exist.interval_type or False
                self.ebay_order_update_next_execution = order_update_cron_exist.nextcall or False
                self.ebay_order_status_update_user_id = order_update_cron_exist.user_id.id or False
      
            # Auto Sync. Active Product
            try:
                auto_sync_active_products_cron_exist = self.env.ref('ebay_ept.ir_cron_auto_sync_active_products_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                auto_sync_active_products_cron_exist = False
            if auto_sync_active_products_cron_exist:
                self.ebay_sync_active_products_interval_number = auto_sync_active_products_cron_exist.interval_number or False
                self.ebay_sync_active_products_interval_type = auto_sync_active_products_cron_exist.interval_type or False
                self.ebay_sync_active_products_next_execution = auto_sync_active_products_cron_exist.nextcall or False
                self.ebay_sync_active_products_user_id = auto_sync_active_products_cron_exist.user_id.id or False
            
            # Auto Sent Invoice Via Mail
            try:
                auto_sent_invoice_via_mail_cron_exist = self.env.ref('ebay_ept.ir_cron_auto_send_invoice_via_mail_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                auto_sent_invoice_via_mail_cron_exist = False
            if auto_sent_invoice_via_mail_cron_exist:
                self.ebay_send_invoice_via_email_interval_number = auto_sent_invoice_via_mail_cron_exist.interval_number or False
                self.ebay_send_invoice_via_email_interval_type = auto_sent_invoice_via_mail_cron_exist.interval_type or False
                self.ebay_send_invoice_via_email_next_execution = auto_sent_invoice_via_mail_cron_exist.nextcall or False
                self.ebay_send_invoice_user_id = auto_sent_invoice_via_mail_cron_exist.user_id.id or False
                    
    @api.multi
    def execute(self):
        values = {}
        instance = self.ebay_instance_id or False
        res = super(ebay_config_settings,self).execute()
        if instance:
            values['is_auto_get_feedback']=self.is_ebay_auto_get_feedback
            values['warehouse_id'] = self.ebay_warehouse_id and self.ebay_warehouse_id.id or False
            values['lang_id'] = self.ebay_lang_id and self.ebay_lang_id.id or False
            values['order_prefix'] = self.ebay_order_prefix and self.ebay_order_prefix
            values['stock_field'] = self.ebay_stock_field and self.ebay_stock_field.id or False
            values['pricelist_id'] = self.ebay_pricelist_id and self.ebay_pricelist_id.id or False             
            values['fiscal_position_id'] = self.ebay_fiscal_position_id and self.ebay_fiscal_position_id.id or False
            values['order_auto_import']=self.ebay_order_auto_import
            values['is_import_shipped_order'] = self.is_ebay_import_shipped_order or False
            values['stock_auto_export']=self.ebay_stock_auto_export
            values['create_new_product']=self.ebay_create_new_product or False
            values['create_quotation_without_product']=self.create_quotation_without_product or False
            values['ebay_order_auto_update']=self.ebay_order_auto_update
            values['ebay_default_product_category_id']=self.ebay_default_product_category_id and self.ebay_default_product_category_id.id or False
            values['pay_mthd']=self.ebay_pay_mthd
            values['email_add']=self.ebay_email_add
            values['site_id']=self.ebay_site_id and self.ebay_site_id.id or False
            values['team_id']=self.ebay_team_id and self.ebay_team_id.id or False
            values['post_code']=self.ebay_post_code or False
            values['price_tax_included']=self.ebay_price_tax_included or False
            values['company_id']=self.ebay_company_id and self.ebay_company_id.id or False
            values['shipment_charge_product_id']=self.ebay_shipment_charge_product_id and self.ebay_shipment_charge_product_id.id or False
            values['discount_charge_product_id']=self.ebay_discount_charge_product_id and self.ebay_discount_charge_product_id.id or False
            values['ebay_plus']=self.ebay_plus or False
            values['tax_id']=self.ebay_tax_id and self.ebay_tax_id.id or False
            values['use_dynamic_desc']=self.ebay_use_dynamic_desc or False
            values['auto_update_payment']=self.ebay_auto_update_payment or False
            values['auto_sync_active_products'] = self.ebay_auto_sync_active_products
            values['sync_active_products_start_date'] = self.ebay_sync_active_products_start_date
            values['auto_send_invoice_via_email'] = self.ebay_auto_send_invoice_via_email
            values['send_invoice_template_id'] = self.ebay_send_invoice_template_id and self.ebay_send_invoice_template_id.id or False
            values['partner_id'] = self.ebay_partner_id and self.ebay_partner_id.id or False
            values['global_channel_id']= self.ebay_global_channel_id and self.ebay_global_channel_id.id or False
            values['product_url']= self.ebay_product_url or False
            values['item_location_country'] = self.ebay_item_location_country and self.ebay_item_location_country.id or False
            values['item_location_name'] = self.ebay_item_location_name or ''

            instance.write(values)
            self.ebay_setup_get_feedback_cron(instance)
            self.ebay_setup_order_import_cron(instance)
            self.ebay_setup_order_status_update_cron(instance)
            self.ebay_setup_update_stock_cron(instance)
            self.ebay_setup_auto_sync_active_products(instance)
            self.ebay_setup_auto_send_invoice_via_mail(instance)
        return res
    
    @api.multi   
    def ebay_setup_get_feedback_cron(self,instance):
        if self.is_ebay_auto_get_feedback:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_get_feedback_%d'%(instance.id),raise_if_not_found=False)
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.get_ebay_feedback_interval_type](self.get_ebay_feedback_interval_number)
            
            vals = {
                    'active' : True,
                    'interval_number':self.get_ebay_feedback_interval_number,
                    'interval_type':self.get_ebay_feedback_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': self.get_ebay_feedback_user_id and self.get_ebay_feedback_user_id.id,
                    'code': "model.auto_get_feedback({'instance_id':%d})"%(instance.id)
                    }
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    getfeedback_cron = self.env.ref('ebay_ept.ir_cron_auto_get_feedback')
                except:
                    getfeedback_cron=False
                if not getfeedback_cron:
                    raise Warning('Core settings of eBay are deleted, please upgrade eBay Connector module to back this settings.')
                
                name = instance.name + ' : ' +getfeedback_cron.name
                vals.update({'name' : name})
                new_cron = getfeedback_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'ebay_ept',
                                                  'name':'ir_cron_get_feedback_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_get_feedback_%d'%(instance.id))
            except:
                cron_exist=False
            
            if cron_exist:
                cron_exist.write({'active':False})
        return True
           
       
    @api.multi   
    def ebay_setup_order_import_cron(self,instance):
        if self.ebay_order_auto_import:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_send_ebay_import_sales_orders_instance_%d'%(instance.id),raise_if_not_found=False)
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.ebay_order_import_interval_type](self.ebay_order_import_interval_number)
            vals = {
                    'active' : True,
                    'interval_number':self.ebay_order_import_interval_number,
                    'interval_type':self.ebay_order_import_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': self.ebay_order_import_user_id and self.ebay_order_import_user_id.id,
                    'code': "model.auto_import_ebay_sales_orders({'instance_id':%d})"%(instance.id)
                    }
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    import_order_cron = self.env.ref('ebay_ept.ir_cron_send_ebay_import_sales_orders')
                except:
                    import_order_cron=False
                if not import_order_cron:
                    raise Warning('Core settings of eBay are deleted, please upgrade eBay Connector module to back this settings.')
                
                name = instance.name + ' : ' +import_order_cron.name
                vals.update({'name' : name})
                new_cron = import_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'ebay_ept',
                                                  'name':'ir_cron_send_ebay_import_sales_orders_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_send_ebay_import_sales_orders_instance_%d'%(instance.id))
            except:
                cron_exist=False
            
            if cron_exist:
                cron_exist.write({'active':False})
        return True                                                                                                                
        
    
    @api.multi   
    def ebay_setup_order_status_update_cron(self,instance):
        if self.ebay_order_auto_update:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_update_order_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.ebay_order_update_interval_type](self.ebay_order_update_interval_number)
            vals = {'active' : True,
                    'interval_number':self.ebay_order_update_interval_number,
                    'interval_type':self.ebay_order_update_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': self.ebay_order_status_update_user_id and self.ebay_order_status_update_user_id.id,
                    'code': "model.auto_update_order_status({'instance_id':%d})"%(instance.id)
                    }
                    
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    update_order_cron = self.env.ref('ebay_ept.ir_cron_update_order_status')
                except:
                    update_order_cron=False
                if not update_order_cron:
                    raise Warning('Core settings of eBay are deleted, please upgrade eBay Connector module to back this settings.')
                
                name = instance.name + ' : ' +update_order_cron.name
                vals.update({'name' : name}) 
                new_cron = update_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'ebay_ept',
                                                  'name':'ir_cron_update_order_status_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_update_order_status_instance_%d'%(instance.id))
            except:
                cron_exist=False
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    
    @api.multi   
    def ebay_setup_update_stock_cron(self,instance):
        if self.ebay_stock_auto_export:
            try:                
                cron_exist = self.env.ref('ebay_ept.ir_cron_auto_export_inventory_instance_%d'%(instance.id))
            except:
                cron_exist=False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.ebay_update_stock_interval_type](self.ebay_update_stock_interval_number)
            vals = {'active' : True,
                    'interval_number':self.ebay_update_stock_interval_number,
                    'interval_type':self.ebay_update_stock_interval_type,
                    'nextcall':nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': self.ebay_stock_update_user_id and self.ebay_stock_update_user_id.id,
                    'code': "model.auto_export_inventory_ept({'instance_id':%d})"%(instance.id)
                    }
            if cron_exist:
                vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                try:                    
                    update_stock_cron = self.env.ref('ebay_ept.ir_cron_auto_export_inventory')
                except:
                    update_stock_cron=False
                if not update_stock_cron:
                    raise Warning('Core settings of eBay are deleted, please upgrade eBay Connector module to back this settings.')
                
                name = instance.name + ' : ' +update_stock_cron.name
                vals.update({'name':name})
                new_cron = update_stock_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'ebay_ept',
                                                  'name':'ir_cron_auto_export_inventory_instance_%d'%(instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_auto_export_inventory_instance_%d'%(instance.id))
            except:
                cron_exist=False
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    
    @api.multi
    def ebay_setup_auto_sync_active_products(self, instance):
        if self.ebay_auto_sync_active_products:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_auto_sync_active_products_instance_%d' % (instance.id),raise_if_not_found=False)
            except:
                cron_exist = False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.ebay_sync_active_products_interval_type](self.ebay_sync_active_products_interval_number)
            vals = {
                'active': True,
                'interval_number': self.ebay_sync_active_products_interval_number,
                'interval_type': self.ebay_sync_active_products_interval_type,
                'nextcall': nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': self.ebay_sync_active_products_user_id and self.ebay_sync_active_products_user_id.id,
                'code': "model.auto_sync_active_products_listings({'instance_id':%d})"%(instance.id)
                }
                
            if cron_exist:
                vals.update({'name': cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    sync_auto_products_cron_ref_id = self.env.ref('ebay_ept.ir_cron_auto_sync_active_products')
                except:
                    sync_auto_products_cron_ref_id = False
                if not sync_auto_products_cron_ref_id:
                    raise Warning(
                        'Core settings of eBay are deleted, please upgrade eBay Connector module to back this settings.')

                name = instance.name + ' : ' + sync_auto_products_cron_ref_id.name
                vals.update({'name': name})
                new_cron = sync_auto_products_cron_ref_id.copy(default=vals)
                self.env['ir.model.data'].create({'module': 'ebay_ept',
                                                  'name': 'ir_cron_auto_sync_active_products_instance_%d' % (instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id': new_cron.id,
                                                  'noupdate': True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_auto_sync_active_products_instance_%d' % (instance.id))
            except:
                cron_exist = False

            if cron_exist:
                cron_exist.write({'active': False})
        return True

    @api.multi
    def ebay_setup_auto_send_invoice_via_mail(self,instance):
        if self.ebay_auto_send_invoice_via_email:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_auto_send_invoice_via_mail_instance_%d' % (instance.id),
                                          raise_if_not_found=False)
            except:
                cron_exist = False
            nextcall = datetime.now()
            nextcall += _intervalTypes[self.ebay_send_invoice_via_email_interval_type](self.ebay_send_invoice_via_email_interval_number)
            vals = {
                'active': True,
                'interval_number': self.ebay_send_invoice_via_email_interval_number,
                'interval_type': self.ebay_send_invoice_via_email_interval_type,
                'nextcall': nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': self.ebay_send_invoice_user_id and self.ebay_send_invoice_user_id.id,
                'code': "model.send_ebay_invoice_via_email({'instance_id':%d})"%(instance.id)
            }
            if cron_exist:
                vals.update({'name': cron_exist.name})
                cron_exist.write(vals)
            else:
                try:
                    send_auto_invoice_cron_ref_id = self.env.ref('ebay_ept.ir_cron_auto_send_invoice_via_mail')
                except:
                    send_auto_invoice_cron_ref_id = False
                if not send_auto_invoice_cron_ref_id:
                    raise Warning(
                        'Core settings of eBay are deleted, please upgrade eBay Connector module to back this settings.')

                name = instance.name + ' : ' + send_auto_invoice_cron_ref_id.name
                vals.update({'name': name})
                new_cron = send_auto_invoice_cron_ref_id.copy(default=vals)
                self.env['ir.model.data'].create({'module': 'ebay_ept',
                                                  'name': 'ir_cron_auto_send_invoice_via_mail_instance_%d' % (
                                                  instance.id),
                                                  'model': 'ir.cron',
                                                  'res_id': new_cron.id,
                                                  'noupdate': True
                                                  })
        else:
            try:
                cron_exist = self.env.ref('ebay_ept.ir_cron_auto_send_invoice_via_mail_instance_%d' % (instance.id))
            except:
                cron_exist = False
            if cron_exist:
                cron_exist.write({'active': False})
        return True