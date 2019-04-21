from odoo import models,fields,api,_
from ..amazon_emipro_api.mws import Sellers
from odoo.exceptions import Warning
from dateutil.relativedelta import relativedelta

_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}
               
"""Added by Dhruvi [20-08-2018]
added field to check whether instance should be active or not"""        
class amazon_instance_ept(models.Model):
    _inherit = 'amazon.instance.ept'
    
    active = fields.Boolean(string='Active',default=True)
    
    @api.multi
    def toggle_active(self):
        """ Inverse the value of the field ``active`` on the records in ``self``. """
        for record in self:
            record.active = not record.active
                
"""Added by Dhruvi [11-08-2018] 
to create multiple marketplace instance as per multiple marketplace selected"""
class amazon_marketplace_config(models.TransientModel):
    _name = 'res.config.amazon.marketplace'
    _description = 'res.config.amazon.marketplace'
      
    marketplace_ids = fields.Many2many('amazon.marketplace.ept','res_config_amazon_marketplace_rel','res_marketplace_id','amazon_market_place_id',string="Marketplaces")
    seller_id = fields.Many2one('amazon.seller.ept',string='Seller')

    """Added by Dhruvi [29-08-2018]
    Method to search FBM warehouse [default or according to seller wise or according to company of user]"""
    @api.multi
    def search_amazon_warehouse(self,company_id):
        default_warehouse = self.env.ref('stock.warehouse0')
        if self.seller_id.company_id == default_warehouse.company_id:
            warehouse_id = default_warehouse.id
        else:  
            warehouse = self.env['stock.warehouse'].search([('company_id','=',company_id.id)])
            if warehouse:
                warehouse_id = warehouse[0].id
            else:
                warehouse = self.env['stock.warehouse'].search([])
                warehouse_id = warehouse and warehouse[0].id
                
        return warehouse_id
    
    def prepare_amazon_marketplace_vals(self,marketplace,warehouse_id,company_id,lang_id):
        vals = {
                'name':marketplace.name,
                'marketplace_id' :marketplace.id,
                'seller_id' : self.seller_id.id,
                'warehouse_id':warehouse_id,
                'company_id' : company_id.id,
                'producturl_prefix':"https://%s/dp/" % marketplace.name,
                'ending_balance_description':'Transfer to Bank',
                'lang_id':lang_id.id,
                }
        
        return vals

    @api.multi
    def create_amazon_marketplace(self):
        ins = []
        account_journal_obj = self.env['account.journal']
        account_obj = self.env['account.account']
        product_pricelist_obj = self.env['product.pricelist']
        res_lang_obj = self.env['res.lang']
        for marketplace in self.marketplace_ids:
            instance_exist = self.env['amazon.instance.ept'].search([('seller_id','=', self.seller_id.id),
                                                ('marketplace_id','=',marketplace.id),
                                                ])
          
            if instance_exist:
                raise Warning('Instance already exist for %s with given Credential.'%(marketplace.name))
              
            if marketplace.seller_id.company_id:
                company_id = self.seller_id.company_id
            else:
                company_id = self.env.user.company_id or False
                
            warehouse_id = self.search_amazon_warehouse(company_id)  

            lang_id = res_lang_obj.search([('code','=','en_US')])
            vals = self.prepare_amazon_marketplace_vals(marketplace,warehouse_id,company_id,lang_id)
              
            try:
                instance = self.env['amazon.instance.ept'].create(vals)
                ins.append(instance.id)
                instance.import_browse_node_ept() #Import the browse node for selected country
            except Exception as e:
                raise Warning('Exception during instance creation.\n %s'%(str(e)))
            
            if marketplace.name.find('.') != -1:
                name=marketplace.name.rsplit('.',1)
                code=self.seller_id.short_code+""+name[1]
            else:
                code=self.seller_id.short_code+""+marketplace.name
                
            journal_id = account_journal_obj.search([('code','=',code)])
            if journal_id:
                instance.update({'settlement_report_journal_id':journal_id.id})
            else:
                journal_vals={
                'name':marketplace.name+"(%s)"%self.seller_id.name,
                'type':'bank',
                'code':code,
                'currency_id':(marketplace.currency_id or marketplace.country_id.currency_id).id   
                }
            
                settlement_journal_id = account_journal_obj.create(journal_vals)
                if not settlement_journal_id.currency_id.active:
                    settlement_journal_id.currency_id.active = True
                instance.update({'settlement_report_journal_id':settlement_journal_id.id})
            
            ending_balance=account_obj.search([('reconcile','=',True),('user_type_id.id', '=', self.env.ref('account.data_account_type_current_assets').id), ('deprecated', '=', False)],limit=1)
            instance.update({'ending_balance_account_id':ending_balance.id})
            
            pricelist_vals={
                'name':marketplace.name+" Pricelist(%s)"%self.seller_id.name,
                'discount_policy':'with_discount',
                'company_id':self.seller_id.company_id.id,
                'currency_id':(marketplace.currency_id or marketplace.country_id.currency_id).id,
                }
            
            pricelist_id =product_pricelist_obj.create(pricelist_vals)
            instance.update({'pricelist_id':pricelist_id.id})
        action = self.env.ref('amazon_ept.action_amazon_configuration', False)
        result = action and action.read()[0] or {}
   
        ctx = result.get('context',{}) and eval(result.get('context'))
        ctx.update({'default_seller_id': instance.seller_id.id})
        result['context'] = ctx
        return ins,result

class amazon_seller_config(models.TransientModel):
    _name = 'res.config.amazon.seller'
    _description = 'res.config.amazon.seller'
    
    name = fields.Char("Seller Name")
    access_key = fields.Char("Access Key")
    secret_key = fields.Char("Secret Key")
    merchant_id = fields.Char("Merchant Id")
    country_id = fields.Many2one('res.country',string = "Country")
    
    #added by Dhruvi
    company_id = fields.Many2one('res.company',string='Company')
    
    #added by dhaval
    developer_id = fields.Many2one('amazon.developer.details.ept', compute="set_developer_id", string="Developer ID",
                                   store=False)
    developer_name = fields.Char("Developer Name")
    is_own_developer_account = fields.Boolean(string="Is Own Developer Account",default=False)
    auth_token = fields.Char("Auth Token")
    
    @api.multi
    def test_amazon_connection(self):
        if self.is_own_developer_account:
            seller_exist = self.env['amazon.seller.ept'].search([('access_key', '=', self.access_key),
                                                                 ('secret_key', '=', self.secret_key),
                                                                 ('merchant_id', '=', self.merchant_id),
                                                                 ('is_own_developer_account', '=', True)
                                                                 ])
        else:
            seller_exist = self.env['amazon.seller.ept'].search([('is_own_developer_account', '=', False),
                                                                 ('auth_token', '=', self.auth_token),
                                                                 ('merchant_id', '=', self.merchant_id)
                                                                 ])

        global_channel_ept_obj = self.env['global.channel.ept']
        if seller_exist:
            raise Warning('Seller already exist with given Credential.')
        

        mws_obj = Sellers(access_key=self.access_key and str(self.access_key) or False,
                          secret_key=self.secret_key and str(self.secret_key) or False,
                          account_id=self.merchant_id and str(self.merchant_id) or False,
                          region=self.country_id.amazon_marketplace_code or self.country_id.code,
                          auth_token=self.auth_token and str(self.auth_token) or False)
        flag = False
        try:
            result = mws_obj.list_marketplace_participations()
            paticipants = result.parsed.get('ListParticipations',{})
            if paticipants:
                flag=True
        except Exception as e:
            raise Warning('Given Credential is incorrect, please provide correct Credential.')
        if flag:
            if self.company_id:
                company_id=self.company_id
            else:
                company_id=self.env.user.company_id or False

            vals = {
                'name': self.name,
                'country_id': self.country_id.id,
                'company_id': company_id.id,
                'merchant_id': self.merchant_id,
            }

            if self.is_own_developer_account:
                vals.update({
                    'access_key': self.access_key,
                    'secret_key': self.secret_key,
                    'is_own_developer_account': True
                })

            else:
                vals.update({
                    'auth_token': self.auth_token,
                    'developer_id': self.developer_id.id,
                    'developer_name': self.developer_name,
                    'is_own_developer_account': False
                })

            """Added by Dhruvi to validate seller Short Code"""
            self.check_seller_short_code(vals)        
            try:
                seller = self.env['amazon.seller.ept'].create(vals)
                
                """added by Dhruvi [11-08-2018] method called to create global channel
                 ,to create unsellable location,to set shipment fees,
                 to set amazon fee account and to set payment term"""
                global_channel_ept_obj.create_global_channel(seller)
                self.set_amaon_fee_account(seller)
                self.create_transaction_type(seller,self.amazon_fee_account)
                seller.load_marketplace()
            
            except Exception as e:
                raise Warning('Exception during instance creation.\n %s'%(str(e)))
                    
            action = self.env.ref('amazon_ept.action_amazon_configuration', False)
            result = action and action.read()[0] or {}
            result.update({'seller_id':seller.id})
            return result
            
        return True

    @api.multi
    def set_developer_id(self):
        self.onchange_country_id()

    @api.onchange('country_id')
    def onchange_country_id(self):
        if self.country_id:
            if self.is_own_developer_account == False:
                developer_id = self.env['amazon.developer.details.ept'].search([('developer_country_id','=',self.country_id.id)])
                self.update({'developer_id' : developer_id.id or False,'developer_name' : developer_id.developer_name or False})
                
    
"""added by Dhruvi [11-08-2018]
method to create global channel as Name of amazon seller and also setting global_channel_id in amazon seller."""
class global_channel_ept(models.Model):
    _inherit = 'global.channel.ept'
      
    @api.model
    def create_global_channel(self,seller):
        channel_vals = {'name':seller.name}
        res = self.create(channel_vals)
        seller.update({'global_channel_id':res.id})  

"""Added by Dhruvi [17-08-2018]
field added into res.config.seller named Amazon Fee Account and have set its value in amazon seller"""
class amazon_config_settings_ept(models.TransientModel):
    _inherit = "res.config.amazon.seller"
    
    amazon_fee_account = fields.Many2one('account.account',string="Amazon Fee Account")
    short_code = fields.Char(string="Short Code",size=2)
    
    
    @api.one
    def check_seller_short_code(self,seller):
        amazon_seller_obj = self.env['amazon.seller.ept']
        seller_code = amazon_seller_obj.search([('short_code','=',self.short_code)])
        if seller_code:
            raise Warning("Short Code should be Unique according to Seller")
        else:
            seller.update({'short_code':self.short_code})
       
    @api.one      
    def set_amaon_fee_account(self,seller):
        seller.update({'amazon_fee_account':self.amazon_fee_account.id})
        
    @api.multi
    def create_transaction_type(self,seller,fee_account):
        trans_line_obj = self.env['amazon.transaction.line.ept']
        trans_type_ids = self.env['amazon.transaction.type'].search([])
        for trans_id in trans_type_ids:
            trans_line_vals = {
                            'transaction_type_id':trans_id.id,
                            'seller_id':seller.id,
                            'amazon_code':trans_id.amazon_code,
                            'account_id':fee_account.id,
                            }
            trans_line_obj.create(trans_line_vals)
            
        
            


    
class amazon_instance_config(models.TransientModel):
    _name = 'res.config.amazon.instance'
    _description = 'res.config.amazon.instance'
    
    name = fields.Char("Instance Name")
    seller_id = fields.Many2one('amazon.seller.ept',string='Seller')
    marketplace_id = fields.Many2one('amazon.marketplace.ept',string='Marketplace',
                                     domain="[('seller_id','=',seller_id),('is_participated','=',True)]")
    
    @api.multi
    def create_amazon_instance(self):
        instance_exist = self.env['amazon.instance.ept'].search([('seller_id','=', self.seller_id.id),
                                                ('marketplace_id','=',self.marketplace_id.id),
                                                ])
        if instance_exist:
            raise Warning('Instance already exist with given Credential.')
        
        
        if self.seller_id.company_id:
            company_id = self.seller_id.company_id.id
        else:
            company_id = self.env.user.company_id and self.env.user.company_id.id or False
            
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_id)])
        if warehouse:
            warehouse_id = warehouse[0].id
        else:
            warehouse = self.env['stock.warehouse'].search([])
            warehouse_id = warehouse and warehouse[0].id
        marketplace=self.marketplace_id
        vals = {
                'name':self.name,
                'marketplace_id' :marketplace.id,
                'seller_id' : self.seller_id.id,
                'warehouse_id':warehouse_id,
                'company_id' : company_id,
                'producturl_prefix':"https://%s/dp/" % self.marketplace_id.name
                }
        try:
            instance = self.env['amazon.instance.ept'].create(vals)
            instance.import_browse_node_ept() #Import the browse node for selected country
        except Exception as e:
            raise Warning('Exception during instance creation.\n %s'%(str(e)))
                
        action = self.env.ref('amazon_ept.action_amazon_configuration', False)
        result = action and action.read()[0] or {}

        ctx = result.get('context',{}) and eval(result.get('context'))
        ctx.update({'default_seller_id': instance.seller_id.id})
        #ctx.update({'default_seller_id': instance.seller_id.id,'default_instance_id': instance.id})
        result['context'] = ctx
        return result
        
        
class amazon_config_settings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    """added by Dhruvi [20-08-2018]
    Method to return seller id in marketplace wizard using context"""
    
    @api.multi
    def create_more_amazon_marketplace(self):
        action = self.env.ref('amazon_ept.res_config_action_amazon_marketplace', False)
        result = action and action.read()[0] or {}

        ctx = result.get('context',{}) and eval(result.get('context'))
        ctx.update({'default_seller_id': self.amz_seller_id.id})
        result['context'] = ctx
        return result
    
    @api.model
    def default_get(self, fields):
        res = super(amazon_config_settings, self).default_get(fields)
        
        cur_usr = self.env['res.users'].browse(self._uid)
        if cur_usr.has_group('amazon_ept.group_amazon_user_ept'):
            check_helpdesk_module_state = self.env['ir.module.module'].search([('name', '=', 'amazon_helpdesk_support_ept')])
            helpdesk =False
            buynow_helpdesk = False
            if check_helpdesk_module_state and check_helpdesk_module_state.state == "installed":
                helpdesk = True
            if not check_helpdesk_module_state:
                buynow_helpdesk = True
            res.update({'install_helpdesk' : helpdesk,'buynow_helpdesk':buynow_helpdesk})
            
            check_manage_customer_returns_state = self.env['ir.module.module'].search([('name', '=', 'amazon_rma_ept')])
            manage_customer =False
            buynow_manage_customer_returns = False
            if check_manage_customer_returns_state and check_manage_customer_returns_state.state == "installed":
                manage_customer = True
            if not check_manage_customer_returns_state:
                buynow_manage_customer_returns = True
            res.update({'manage_customer_returns' : manage_customer,'buynow_manage_customer_returns':buynow_manage_customer_returns})
    
        return res
    
#     @api.model
#     def _default_seller(self):
#         cur_usr = self.env['res.users'].browse(self._uid)
#         if cur_usr.has_group('amazon_ept.group_amazon_user_ept'):
#             sellers = self.env['amazon.seller.ept'].search([])
#             if len(sellers.ids)>1:
#                 return False
#             else:
#                 return sellers and sellers[0].id or False
#          
#     @api.model
#     def _default_instance(self):
#         cur_usr = self.env['res.users'].browse(self._uid)
#         if cur_usr.has_group('amazon_ept.group_amazon_user_ept'):
#             if self.amz_seller_id:
#                 seller_id = self.amz_seller_id.id
#                 instances = self.env['amazon.instance.ept'].search([('seller_id','=',seller_id)])
#                 if len(self.instances.ids):
#                     return False
#                 else:
#                     return instances and instances[0].id or False
#             else:
#                 return False
#     @api.model
#     def _get_default_company(self):
#         cur_usr = self.env['res.users'].browse(self._uid)
#         if cur_usr.has_group('amazon_ept.group_amazon_user_ept'):
#             company_id = self.env.user._get_company()
#             if not company_id:
#                 raise Warning(_('There is no default company for the current user!'))
#             return company_id
        
    amz_seller_id = fields.Many2one('amazon.seller.ept',string='Amazon Seller')     
    amz_instance_id = fields.Many2one('amazon.instance.ept',string='Amazon Instance')
    amz_warehouse_id = fields.Many2one('stock.warehouse',string = "Amazon Warehouse")
    company_for_amazon_id = fields.Many2one('res.company',string='Company Name')
    amz_country_id = fields.Many2one('res.country',string = "Country Name")
    amz_partner_id = fields.Many2one('res.partner', string='Default Customer')
    amz_lang_id = fields.Many2one('res.lang', string='Language Name')
    amz_team_id=fields.Many2one('crm.team', 'Amazon Sales Team')
    #commented by dhavals 9-2-2019
    #extra field
    #amz_fulfillment_by = fields.Selection([('MFN','Manufacturer Fulfillment Network'),('AFN','Amazon Fulfillment Network')],string="Fulfillment By",default='MFN')
    amz_auto_workflow_id = fields.Many2one('sale.workflow.process.ept', string='Amazon Auto Workflow')
    amz_order_prefix = fields.Char(size=10, string='Amazon Order Prefix')
    
    amz_price_tax_included = fields.Boolean(string='Is Price Tax Included?')
    
    amz_instance_stock_field = fields.Many2one('ir.model.fields', string='Product Stock Field', 
        domain="[('model', 'in', ['product.product', 'product.template']), ('type', '=', 'float')]")
    
    amz_update_stock_on_fly = fields.Boolean("Auto Update Stock On the Fly ?",default=False,help='If it is ticked, real time stock updated in Amazon.')
    amz_customer_is_company = fields.Boolean("Customer is Company ?",default=False)
    amz_instance_pricelist_id = fields.Many2one('product.pricelist', string='Pricelist Name')
    amz_payment_term_id = fields.Many2one('account.payment.term', string='Payment Term Name')
    
    amz_shipment_charge_product_id=fields.Many2one("product.product","Amazon Shipment Fee",domain=[('type','=','service')])
    amz_gift_wrapper_product_id=fields.Many2one("product.product","Amazon Gift Wrapper Fee",domain=[('type','=','service')])
    amz_promotion_discount_product_id=fields.Many2one("product.product","Amazon Promotion Discount",domain=[('type','=','service')])
    amz_ship_discount_product_id = fields.Many2one("product.product","Amazon Shipment Discount",domain=[('type','=','service')])
    
    amz_instance_fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position Name')
    amz_instance_tax_id = fields.Many2one('account.tax', string='Default Sales Tax')
    amz_instance_settlement_report_journal_id = fields.Many2one('account.journal',string='Settlement Report Journal')

    amz_condition = fields.Selection([('New','New'),
                                  ('UsedLikeNew','UsedLikeNew'),
                                  ('UsedVeryGood','UsedVeryGood'),
                                  ('UsedGood','UsedGood'),
                                  ('UsedAcceptable','UsedAcceptable'),
                                  ('CollectibleLikeNew','CollectibleLikeNew'),
                                  ('CollectibleVeryGood','CollectibleVeryGood'),
                                  ('CollectibleGood','CollectibleGood'),
                                  ('CollectibleAcceptable','CollectibleAcceptable'),
                                  ('Refurbished','Refurbished'),
                                  ('Club','Club')],string="Product Condition",default='New',copy=False)
    
    """Change by Dhruvi [17-08-2018] default= True for return and refund"""
    amz_auto_create_return_picking=fields.Boolean("Auto Create Return Picking ?",default=True)
    amz_auto_create_refund=fields.Boolean("Auto Create Refund ?",default=True)
    
    #commented by dhaval 26-2-2019
    #no more field required
    #amz_instance_send_order_acknowledgment=fields.Boolean("Order Acknowledgment required ?")
    #amz_instance_allow_order_adjustment=fields.Boolean("Allow Order Adjustment ?")
    
    amz_product_ads_account = fields.Boolean('Configure Product Advertising Account ?')
    amz_pro_advt_access_key=fields.Char("Product Advertising Access Key")
    amz_pro_advt_scrt_access_key=fields.Char("Product Advertising Secret Key")
    amz_pro_advt_associate_tag=fields.Char("Product Advertising Associate Tag")
    
    amz_stock_auto_export=fields.Boolean(string="Auto Export Stock ?")
    amz_inventory_export_next_execution = fields.Datetime('Inventory Export Next Execution', help='Export Inventory Next execution time')
    amz_inventory_export_interval_number = fields.Integer('Export stock Interval Number',help="Repeat every x.")
    amz_inventory_export_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Export Stock Interval Unit')
    amz_inventory_export_user_id=fields.Many2one("res.users",string="Inventory Export User")
    
    amz_order_auto_update = fields.Boolean("Auto Update FBM Order Status?",default=False)
    amz_order_update_next_execution = fields.Datetime('FBM Order Update Next Execution', help='Next execution time')
    amz_order_update_interval_number = fields.Integer('FBM Order Update Interval Number',help="Repeat every x.")
    amz_order_update_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'FBM Order Update Interval Unit')    
    amz_order_update_user_id=fields.Many2one("res.users",string="FBM Order Update User")
    amz_settlement_report_auto_create = fields.Boolean("Auto Import Settlement Report ?",default=False)
    amz_settlement_report_create_next_execution = fields.Datetime('Settlement Report Create Next Execution', help='Next execution time')
    amz_settlement_report_create_interval_number = fields.Integer('Settlement Report Create Interval Number',help="Repeat every x.")
    amz_settlement_report_create_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Settlement Report Create Interval Unit')    
    amz_settlement_report_create_user_id=fields.Many2one("res.users",string="Settlement Report Create User")

    amz_settlement_report_auto_process = fields.Boolean("Auto Process Settlement Report ?",default=False)
    amz_settlement_report_process_next_execution = fields.Datetime('Settlement Report Process Next Execution', help='Next execution time')
    amz_settlement_report_process_interval_number = fields.Integer('Settlement Report Process Interval Number',help="Repeat every x.")
    amz_settlement_report_process_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Settlement Report Process Interval Unit')    
    amz_settlement_report_process_user_id=fields.Many2one("res.users",string="Settlement Report Process User")
            
    amz_auto_send_invoice=fields.Boolean("Auto Send Invoice Via Email ?",default=False)
    amz_auto_send_invoice_next_execution = fields.Datetime('Auto Send Invoice Next Execution', help='Next execution time')
    amz_auto_send_invoice_interval_number = fields.Integer('Auto Send Invoice Interval Number',help="Repeat every x.")
    amz_auto_send_invoice_process_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Auto Send Invoice Interval Unit')    
    amz_auto_send_invoice_user_id=fields.Many2one("res.users",string="Auto Send Invoice User")
    amz_instance_invoice_tmpl_id=fields.Many2one("mail.template",string="Invoice Template",default=False)
    #auto send refund
    amz_auto_send_refund=fields.Boolean("Auto Send Refund Via Email ?", default=False)
    amz_auto_send_refund_next_execution = fields.Datetime('Auto Send Refund Next Execution', help='Next execution time')
    amz_auto_send_refund_interval_number = fields.Integer('Auto Send Refund Interval Number',help="Repeat every x.")
    amz_auto_send_refund_process_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Auto Send Refund Process Interval Unit')    
    amz_auto_send_refund_user_id=fields.Many2one("res.users",string="Auto Send Refund User")
    amz_instance_refund_tmpl_id=fields.Many2one("mail.template",string="Refund Template",default=False)

    amz_create_new_product = fields.Boolean('Allow to create new product if not found in odoo ?', default=False)

    amz_instance_manage_multi_tracking_number_in_delivery_order=fields.Boolean("One order can have multiple Tracking Number ?",default=False)
    is_default_odoo_sequence_in_sales_order_fbm=fields.Boolean("Is default Odoo Sequence in Sales Orders (FBM) ?")
    amz_instance_ending_balance_account_id=fields.Many2one('account.account',string="Ending Balance Account")
    amz_instance_ending_balance_description=fields.Char("Ending Balance Description")
    amz_create_sale_order_from_flat_or_xml_report=fields.Selection([('api','API'),('xml', 'Xml'),('flat','Flat')],string="Create FBM Sale Order From?",default="api")    
    amz_order_auto_import=fields.Boolean(string='Auto Import FBM Order?')#import  order  
    amz_order_import_next_execution = fields.Datetime('FBM Order Import Next Execution', help='Next execution time')
    amz_order_import_interval_number = fields.Integer('FBM Order Import Interval Number',help="Repeat every x.")
    amz_order_import_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'FBM Order Import Interval Unit')
    amz_order_import_user_id=fields.Many2one("res.users",string="FBM Order Import User")

    amz_import_shipped_fbm_orders=fields.Boolean("Import FBM Shipped Orders")# import shipped 
       
    amz_auto_process_sale_order_report = fields.Boolean(string='Auto Process FBM Sale Order Report?')#process report   
    amz_process_sale_order_report_next_execution = fields.Datetime('Process FBM Sale Order Report Next Execution', help='Next execution time')
    amz_process_sale_order_report_interval_number = fields.Integer('Process FBM Sale Order Report Interval Number',help="Repeat every x.")
    amz_process_sale_order_report_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Process FBM Sale Order Report Interval Unit')
    
    amz_order_auto_import_xml_or_flat=fields.Boolean(string='Auto Import FBM Sale Order Report?')#import  order  By report
    amz_order_auto_import_xml_or_flat_next_execution = fields.Datetime('Auto Import FBM Sale Order Report Next Execution', help='Next execution time')
    amz_order_auto_import_xml_or_flat_interval_number = fields.Integer('Auto Import FBM Sale Order Report Interval Number',help="Repeat every x.")
    amz_order_auto_import_xml_or_flat_interval_type = fields.Selection( [('minutes', 'Minutes'),
            ('hours','Hours'),  ('days', 'Days'),('weeks', 'Weeks'), ('months', 'Months')], 'Auto Import FBM Sale Order Report Interval Unit')
    amz_order_auto_import_xml_or_flat_user_id=fields.Many2one("res.users",string="Auto Import FBM Sale Order Report User")
    amz_is_another_soft_create_fbm_reports=fields.Boolean(string="Does another tool create the FBM reports?",default=False)
    amz_group_hide_sale_order_report_menu=fields.Boolean('Hide Sale Order Report Menu',compute='hide_menu',implied_group='amazon_ept.group_hide_order_report_menu',default=False)
    
    #added by dhruvi
    install_helpdesk = fields.Boolean(string="Get Customer message and create helpdesk ticket?")#for helpdesk support
    manage_customer_returns = fields.Boolean(string="Manage customer returns & refunds using RMA?")
    amz_global_channel_id = fields.Many2one('global.channel.ept',string='Global Channel')
    buynow_helpdesk = fields.Boolean(string="Buy now")
    buynow_manage_customer_returns = fields.Boolean(string="Buy now Customer Return")
    amz_instance_producturl_prefix = fields.Char(string="Product URL")
    
    #commentd by dhavals 11-2-2019
    #it is not used in whole file in py and xml
    #seller_company_id = fields.Many2one('res.company',string='Seller Company')

    #added by dhaval
    #first time set in Last_FBM_Order_Sync_Time in Seller
    amz_import_shipped_fbm_orders_date = fields.Datetime("Import Shipped FBM Order Time")
    amz_last_import_fbm_order_days = fields.Integer(string="Last Import FBM Order Days")

    @api.multi
    def hide_menu(self):  
        cur_usr = self.env['res.users'].browse(self._uid)
        if cur_usr.has_group('amazon_ept.group_amazon_user_ept'):
            if self.amz_create_sale_order_from_flat_or_xml_report=='api' and not self.amz_seller_id.hide_menu() :           
                self.update({'amz_group_hide_sale_order_report_menu':False})
                return  
            self.update({'amz_group_hide_sale_order_report_menu':True})
    @api.multi   
    def setup_xml_or_flat_report_process_cron(self,seller):
        if self.amz_create_sale_order_from_flat_or_xml_report=='flat' and self.amz_auto_process_sale_order_report:           
            if self.amz_auto_process_sale_order_report:
                cron_exist = self.env.ref('amazon_ept.ir_cron_process_amazon_orders_flat_seller_%d'%(seller.id),raise_if_not_found=False)
                vals = {
                        'active' : True,
                        'interval_number':self.amz_process_sale_order_report_interval_number,
                        'interval_type':self.amz_process_sale_order_report_interval_type,
                        'nextcall':self.amz_process_sale_order_report_next_execution,
                        'code':"model.auto_process_fbm_flat_report({'seller_id':%d})"%(seller.id)}
                        
                if cron_exist:
                    #vals.update({'name' : cron_exist.name})
                    cron_exist.write(vals)
                else:
                    import_order_cron = self.env.ref('amazon_ept.ir_cron_process_amazon_orders_flat',raise_if_not_found=False)
                    if not import_order_cron:
                        raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                    
                    name = 'FBM-'+seller.name + ' : Process Amazon FBM Orders Report'
                    vals.update({'name' : name})
                    new_cron = import_order_cron.copy(default=vals)
                    self.env['ir.model.data'].create({'module':'amazon_ept',
                                                      'name':'ir_cron_process_amazon_orders_flat_seller_%d'%(seller.id),
                                                      'model': 'ir.cron',
                                                      'res_id' : new_cron.id,
                                                      'noupdate' : True
                                                      })
            else:
                cron_exist = self.env.ref('amazon_ept.ir_cron_process_amazon_orders_flat_seller_%d'%(seller.id),raise_if_not_found=False)
                if cron_exist:
                    cron_exist.write({'active':False})
            return True
        
        if self.amz_create_sale_order_from_flat_or_xml_report=='xml':
            if self.amz_auto_process_sale_order_report:
                cron_exist = self.env.ref('amazon_ept.ir_cron_process_amazon_orders_xml_seller_%d'%(seller.id),raise_if_not_found=False)
                vals = {
                        'active' : True,
                        'interval_number':self.amz_process_sale_order_report_interval_number,
                        'interval_type':self.amz_process_sale_order_report_interval_type,
                        'nextcall':self.amz_process_sale_order_report_next_execution,
                        'code':"model.auto_process_fbm_xml_report({'seller_id':%d})"%(seller.id)}
                        
                if cron_exist:
                    #vals.update({'name' : cron_exist.name})
                    cron_exist.write(vals)
                else:
                    import_order_cron = self.env.ref('amazon_ept.ir_cron_process_amazon_orders_xml',raise_if_not_found=False)
                    if not import_order_cron:
                        raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                    
                    name = 'FBM-'+seller.name + ' : Process Amazon FBM Orders Report'
                    vals.update({'name' : name})
                    new_cron = import_order_cron.copy(default=vals)
                    self.env['ir.model.data'].create({'module':'amazon_ept',
                                                      'name':'ir_cron_process_amazon_orders_xml_seller_%d'%(seller.id),
                                                      'model': 'ir.cron',
                                                      'res_id' : new_cron.id,
                                                      'noupdate' : True
                                                      })
            else:
                cron_exist = self.env.ref('amazon_ept.ir_cron_process_amazon_orders_xml_seller_%d'%(seller.id),raise_if_not_found=False)
                if cron_exist:
                    cron_exist.write({'active':False})
            return True
        return False
    @api.one
    @api.constrains('amz_warehouse_id','company_for_amazon_id')
    def onchange_company_warehouse_id(self):
        if self.amz_warehouse_id and self.company_for_amazon_id and self.amz_warehouse_id.company_id.id != self.company_for_amazon_id.id:
            raise Warning("Company in warehouse is different than the selected company. Selected Company and Company in Warehouse must be same.")
   

    @api.onchange('amz_seller_id')
    def onchange_amz_seller_id(self):
        vals = {}
        domain = {}
        if self.amz_seller_id:
            seller = self.env['amazon.seller.ept'].browse(self.amz_seller_id.id)
            instances = self.env['amazon.instance.ept'].search([('seller_id','=',self.amz_seller_id.id)])
            vals = self.onchange_amz_instance_id()
            vals['value']['company_for_amazon_id'] = seller.company_id and seller.company_id.id or False
            vals['value']['company_id']= seller.company_id and seller.company_id.id or False
            vals['value']['amz_order_auto_update'] = seller.order_auto_update or False
            vals['value']['amz_stock_auto_export'] = seller.stock_auto_export or False
            vals['value']['amz_settlement_report_auto_create'] = seller.settlement_report_auto_create or False
            vals['value']['amz_settlement_report_auto_process'] = seller.settlement_report_auto_process or False
            vals['value']['amz_auto_send_invoice']=seller.auto_send_invoice or False
            vals['value']['amz_auto_send_refund']=seller.auto_send_refund or False
            vals['value']['amz_create_new_product']=seller.create_new_product or False                
            vals['value']['amz_order_auto_import']=seller.order_auto_import or False  
            vals['value']['amz_order_auto_import_xml_or_flat']=seller.order_auto_import_xml_or_flat or False         
            vals['value']['amz_import_shipped_fbm_orders'] = seller.import_shipped_fbm_orders or False        
            vals['value']['amz_auto_process_sale_order_report'] = seller.auto_process_sale_order_report or False #process report
            vals['value']['amz_is_another_soft_create_fbm_reports']=seller.is_another_soft_create_fbm_reports or False
            vals['value']['amz_create_sale_order_from_flat_or_xml_report']=seller.create_sale_order_from_flat_or_xml_report or False
             
            #added by Dhruvi 
            vals['value']['amz_global_channel_id'] = seller.global_channel_id and seller.global_channel_id.id or False
            vals['value']['amz_shipment_charge_product_id'] = seller.shipment_charge_product_id and seller.shipment_charge_product_id.id or False
            vals['value']['amz_gift_wrapper_product_id'] = seller.gift_wrapper_product_id and seller.gift_wrapper_product_id.id or False
            vals['value']['amz_promotion_discount_product_id'] = seller.promotion_discount_product_id and seller.promotion_discount_product_id.id or False
            vals['value']['amz_ship_discount_product_id'] = seller.ship_discount_product_id and seller.ship_discount_product_id.id or False
            vals['value']['amz_order_prefix']=seller.order_prefix and seller.order_prefix
            vals['value']['is_default_odoo_sequence_in_sales_order_fbm']=seller.is_default_odoo_sequence_in_sales_order or False
            vals['value']['amz_auto_create_return_picking'] = seller.auto_create_return_picking or False
            vals['value']['amz_auto_create_refund'] = seller.auto_create_refund or False
            vals['value']['amz_payment_term_id'] = seller.payment_term_id and seller.payment_term_id.id or False 
            vals['value']['amz_condition'] = seller.condition or 'New'
            vals['value']['amz_auto_workflow_id'] = seller.auto_workflow_id and seller.auto_workflow_id.id or False
             
            #added by dhaval
            vals['value']['amz_import_shipped_fbm_orders_date'] = seller.import_shipped_fbm_orders_date or False
            vals['value']['amz_last_import_fbm_order_days'] = seller.last_import_fbm_order_days or False
             
            not self.amz_instance_id and vals['value'].update({'amz_instance_id':instances and instances[0].id})
            domain['amz_instance_id'] = [('id','in',instances.ids)]
             
            #comment by dhavals 11-2-2019
            #this cron id is not exists
            #order_process_cron_exist = self.env.ref('amazon_ept.ir_cron_process_amazon_orders_seller_%d'%(seller.id),raise_if_not_found=False)
            #if order_process_cron_exist:
            #    vals['value']['order_process_interval_number'] = order_process_cron_exist.interval_number or False
            #    vals['value']['order_process_interval_type'] = order_process_cron_exist.interval_type or False
            #    vals['value']['amz_process_sale_order_report_next_execution'] = order_process_cron_exist.nextcall or False
          
            order_import_cron_exist = self.env.ref('amazon_ept.ir_cron_import_amazon_orders_seller_%d'%(seller.id),raise_if_not_found=False)
            if order_import_cron_exist:
                vals['value']['amz_order_import_interval_number'] = order_import_cron_exist.interval_number or False
                vals['value']['amz_order_import_interval_type'] = order_import_cron_exist.interval_type or False
                vals['value']['amz_order_import_next_execution'] = order_import_cron_exist.nextcall or False
                vals['value']['amz_order_import_user_id']=order_import_cron_exist.user_id.id or False
            order_update_cron_exist = self.env.ref('amazon_ept.ir_cron_auto_update_order_status_seller_%d'%(seller.id),raise_if_not_found=False)
            if order_update_cron_exist:
                vals['value']['amz_order_update_interval_number'] = order_update_cron_exist.interval_number or False
                vals['value']['amz_order_update_interval_type'] = order_update_cron_exist.interval_type or False
                vals['value']['amz_order_update_next_execution'] = order_update_cron_exist.nextcall or False
                vals['value']['amz_order_update_user_id']=order_update_cron_exist.user_id.id or False
  
            inventory_cron_exist = self.env.ref('amazon_ept.ir_cron_auto_export_inventory_seller_%d'%(seller.id),raise_if_not_found=False)
            if inventory_cron_exist:
                vals['value']['amz_inventory_export_interval_number'] = inventory_cron_exist.interval_number or False
                vals['value']['amz_inventory_export_interval_type'] = inventory_cron_exist.interval_type or False
                vals['value']['amz_inventory_export_next_execution'] = inventory_cron_exist.nextcall or False                                            
                vals['value']['amz_inventory_export_user_id']=inventory_cron_exist.user_id.id or False
            settlement_report_create_cron_exist = self.env.ref('amazon_ept.ir_cron_auto_import_settlement_report_seller_%d'%(seller.id),raise_if_not_found=False)
            if settlement_report_create_cron_exist:
                vals['value']['amz_settlement_report_create_next_execution'] = settlement_report_create_cron_exist.nextcall or False
                vals['value']['amz_settlement_report_create_interval_number'] = settlement_report_create_cron_exist.interval_number or False
                vals['value']['amz_settlement_report_create_interval_type'] = settlement_report_create_cron_exist.interval_type or False                                            
                vals['value']['amz_settlement_report_create_user_id'] = settlement_report_create_cron_exist.user_id.id or False                                            
  
            settlement_report_process_cron_exist = self.env.ref('amazon_ept.ir_cron_auto_process_settlement_report_seller_%d'%(seller.id),raise_if_not_found=False)
            if settlement_report_process_cron_exist:
                vals['value']['amz_settlement_report_process_next_execution'] = settlement_report_process_cron_exist.nextcall or False
                vals['value']['amz_settlement_report_process_interval_number'] = settlement_report_process_cron_exist.interval_number or False
                vals['value']['amz_settlement_report_process_interval_type'] = settlement_report_process_cron_exist.interval_type or False                                            
                vals['value']['amz_settlement_report_process_user_id'] = settlement_report_process_cron_exist.user_id.id or False                                            
  
            send_auto_invoice_cron_exist=self.env.ref('amazon_ept.ir_cron_send_amazon_invoice_via_email_seller_%d'%(seller.id),raise_if_not_found=False)
            if send_auto_invoice_cron_exist:
                vals['value']['amz_auto_send_invoice_next_execution'] = send_auto_invoice_cron_exist.nextcall or False
                vals['value']['amz_auto_send_invoice_interval_number'] = send_auto_invoice_cron_exist.interval_number or False
                vals['value']['amz_auto_send_invoice_process_interval_type'] = send_auto_invoice_cron_exist.interval_type or False                                            
                vals['value']['amz_auto_send_invoice_user_id']=send_auto_invoice_cron_exist.user_id.id or False
              
            send_auto_refund_cron_exist=self.env.ref('amazon_ept.ir_cron_send_amazon_refund_via_email_seller_%d'%(seller.id),raise_if_not_found=False)
            if send_auto_refund_cron_exist:
                vals['value']['amz_auto_send_refund_next_execution'] = send_auto_refund_cron_exist.nextcall or False
                vals['value']['amz_auto_send_refund_interval_number'] = send_auto_refund_cron_exist.interval_number or False
                vals['value']['amz_auto_send_refund_process_interval_type'] = send_auto_refund_cron_exist.interval_type or False                                            
                vals['value']['amz_auto_send_refund_user_id']=send_auto_refund_cron_exist.user_id.id or False
             
            order_auto_import_xml_or_flat_cron_exist=self.env.ref('amazon_ept.ir_cron_xml_or_flat_import_amazon_orders_seller_%d'%(seller.id),raise_if_not_found=False)
            if order_auto_import_xml_or_flat_cron_exist:
                vals['value']['amz_order_auto_import_xml_or_flat_next_execution'] = order_auto_import_xml_or_flat_cron_exist.nextcall or False
                vals['value']['amz_order_auto_import_xml_or_flat_interval_number'] = order_auto_import_xml_or_flat_cron_exist.interval_number or False
                vals['value']['amz_order_auto_import_xml_or_flat_interval_type'] = order_auto_import_xml_or_flat_cron_exist.interval_type or False                                            
                vals['value']['amz_order_auto_import_xml_or_flat_user_id']=order_auto_import_xml_or_flat_cron_exist.user_id.id or False
             
            auto_process_sale_order_report_cron_exist=False
            if seller.create_sale_order_from_flat_or_xml_report=='flat':                
                auto_process_sale_order_report_cron_exist=self.env.ref('amazon_ept.ir_cron_process_amazon_orders_flat_seller_%d'%(seller.id),raise_if_not_found=False)
            elif seller.create_sale_order_from_flat_or_xml_report=='xml':
                auto_process_sale_order_report_cron_exist=self.env.ref('amazon_ept.ir_cron_process_amazon_orders_xml_seller_%d'%(seller.id),raise_if_not_found=False)
            if auto_process_sale_order_report_cron_exist:
                vals['value']['amz_process_sale_order_report_next_execution'] = auto_process_sale_order_report_cron_exist.nextcall or False
                vals['value']['amz_process_sale_order_report_interval_number'] = auto_process_sale_order_report_cron_exist.interval_number or False                                            
                vals['value']['amz_process_sale_order_report_interval_type']=auto_process_sale_order_report_cron_exist.interval_type or False
                          
        else:
            vals = self.onchange_amz_instance_id()            
            vals['value']['amz_order_auto_update'] = False
            vals['value']['amz_stock_auto_export'] = False
            vals['value']['amz_settlement_report_auto_create'] = False
            vals['value']['amz_settlement_report_auto_process'] = False
            vals['value']['amz_auto_send_invoice'] = False
            vals['value']['amz_auto_send_refund'] = False
            vals['value']['amz_instance_id']=False
            domain['amz_instance_id'] = [('id','in',[])]
        vals.update({'domain' : domain})    
        return vals
         
 
    @api.onchange('amz_instance_id')
    def onchange_amz_instance_id(self):
        values = {}
             
        instance = self.amz_instance_id
        if instance:            
            values['amz_instance_id'] = instance.id or False
            values['amz_warehouse_id'] = instance.warehouse_id and instance.warehouse_id.id or False
            values['amz_country_id'] = instance.country_id and instance.country_id.id or False
            values['amz_partner_id'] = instance.partner_id and instance.partner_id.id or False 
            values['amz_lang_id'] = instance.lang_id and instance.lang_id.id or False
            values['amz_team_id']=instance.team_id and instance.team_id.id or False
            values['amz_price_tax_included'] = instance.price_tax_included or False
            values['amz_instance_stock_field'] = instance.stock_field and instance.stock_field.id or False
            values['amz_instance_pricelist_id'] = instance.pricelist_id and instance.pricelist_id.id or False
 
             
            """Commented by Dhruvi as these fields are added in amazon seller"""
 
            #commented by dhaval 26-2-2019
            #no more field required
            #values['amz_instance_send_order_acknowledgment'] = instance.send_order_acknowledgment or False
            #values['amz_instance_allow_order_adjustment'] = instance.allow_order_adjustment or False
            
            values['amz_instance_fiscal_position_id'] = instance.fiscal_position_id and instance.fiscal_position_id.id or False
            values['amz_instance_tax_id'] = instance.tax_id and instance.tax_id.id or False
 
            values['amz_update_stock_on_fly'] = instance.update_stock_on_fly or False
            values['amz_customer_is_company'] = instance.customer_is_company or False
            values['amz_instance_settlement_report_journal_id']=instance.settlement_report_journal_id or False
            values['amz_instance_manage_multi_tracking_number_in_delivery_order']=instance.manage_multi_tracking_number_in_delivery_order or False
            values['amz_instance_invoice_tmpl_id']=instance.invoice_tmpl_id.id or False
            values['amz_instance_refund_tmpl_id']=instance.refund_tmpl_id.id or False
            values['amz_instance_producturl_prefix']= instance.producturl_prefix or ''
             
            if instance.pro_advt_access_key and instance.pro_advt_scrt_access_key and instance.pro_advt_associate_tag:
                values['amz_product_ads_account'] = True
            else:
                values['amz_product_ads_account'] = False    
            values['amz_pro_advt_access_key'] = instance.pro_advt_access_key or False
            values['amz_pro_advt_scrt_access_key'] = instance.pro_advt_scrt_access_key or False
            values['amz_pro_advt_associate_tag'] = instance.pro_advt_associate_tag or False
            values['amz_instance_ending_balance_account_id']=instance.ending_balance_account_id and instance.ending_balance_account_id.id or False
            values['amz_instance_ending_balance_description']=instance.ending_balance_description or False
        else:
            values = {'amz_instance_id':False,'amz_instance_stock_field': False, 'amz_country_id': False, 'amz_price_tax_included': False, 'amz_lang_id': False, 'amz_warehouse_id': False, 'amz_instance_pricelist_id': False, 'amz_partner_id': False}
        return {'value': values}

    @api.multi
    def execute(self):
        
        #added by Dhruvi
        #to install helpdesk support module
        if self.install_helpdesk:
            helpdesk_module = self.env['ir.module.module'].search([('name', '=', 'amazon_helpdesk_support_ept')])
            if not helpdesk_module:
                self.install_helpdesk = False
                self._cr.commit()
                raise Warning('No module Amazon Helpdesk Support found')
            if helpdesk_module and helpdesk_module.state=='to install':
                helpdesk_module.button_install_cancel()
                helpdesk_module.button_immediate_install()
            if helpdesk_module and helpdesk_module.state not in ('installed'):
                helpdesk_module.button_immediate_install()
               
        if self.manage_customer_returns:
            manage_customer_returns_module = self.env['ir.module.module'].search([('name', '=', 'amazon_rma_ept')])
            if not manage_customer_returns_module:
                self.manage_customer_returns = False
                self._cr.commit()
                raise Warning('No module Handle Amazon Returns with RMA found')
            if manage_customer_returns_module and manage_customer_returns_module.state=='to install':
                manage_customer_returns_module.button_install_cancel()
                manage_customer_returns_module.button_immediate_install()
            if manage_customer_returns_module and manage_customer_returns_module.state not in ('installed'):
                manage_customer_returns_module.button_immediate_install()
            
    
        instance = self.amz_instance_id
        values = {}
        res = super(amazon_config_settings,self).execute()
        ctx = {}
        if instance:
            ctx.update({'default_instance_id': instance.id})
           
            values['warehouse_id'] = self.amz_warehouse_id and self.amz_warehouse_id.id or False
            values['country_id'] = self.amz_country_id and self.amz_country_id.id or False
            values['partner_id'] = self.amz_partner_id and self.amz_partner_id.id or False 
            values['lang_id'] = self.amz_lang_id and self.amz_lang_id.id or False
            values['price_tax_included'] = self.amz_price_tax_included or False
            values['stock_field'] = self.amz_instance_stock_field and self.amz_instance_stock_field.id or False
            values['pricelist_id'] = self.amz_instance_pricelist_id and self.amz_instance_pricelist_id.id or False

            #commented by dhaval 26-2-2019
            #no more field required
            #values['send_order_acknowledgment'] = self.amz_instance_send_order_acknowledgment or False
            #values['allow_order_adjustment'] = self.amz_instance_allow_order_adjustment or False            
            
            values['fiscal_position_id'] = self.amz_instance_fiscal_position_id and self.amz_instance_fiscal_position_id.id or False
            values['settlement_report_journal_id']=self.amz_instance_settlement_report_journal_id and self.amz_instance_settlement_report_journal_id.id or False
            values['tax_id'] = self.amz_instance_tax_id and self.amz_instance_tax_id.id or False

            values['update_stock_on_fly'] = self.amz_update_stock_on_fly or False
            values['team_id']=self.amz_team_id and self.amz_team_id.id or False
            values['manage_multi_tracking_number_in_delivery_order']=self.amz_instance_manage_multi_tracking_number_in_delivery_order or False
            
            values['ending_balance_account_id']=self.amz_instance_ending_balance_account_id and self.amz_instance_ending_balance_account_id.id or False
            values['ending_balance_description']=self.amz_instance_ending_balance_description or False
            customer_is_company = True if self.amz_customer_is_company and not self.amz_partner_id else False
            values['customer_is_company'] = customer_is_company 
            values['invoice_tmpl_id']=self.amz_instance_invoice_tmpl_id.id or False
            values['refund_tmpl_id']=self.amz_instance_refund_tmpl_id.id or False
            values['producturl_prefix']= self.amz_instance_producturl_prefix or ''
            
            
            if self.amz_product_ads_account:
                values['pro_advt_access_key'] = self.amz_pro_advt_access_key or False
                values['pro_advt_scrt_access_key'] = self.amz_pro_advt_scrt_access_key or False
                values['pro_advt_associate_tag'] = self.amz_pro_advt_associate_tag or False            
            instance.write(values)
            self.update_user_groups_ept(self.amz_instance_manage_multi_tracking_number_in_delivery_order)
        if self.amz_seller_id :
            vals = {}        
            vals['order_auto_update'] = self.amz_order_auto_update or False
            vals['stock_auto_export'] = self.amz_stock_auto_export or False
            vals['settlement_report_auto_create']=self.amz_settlement_report_auto_create or False
            vals['settlement_report_auto_process']=self.amz_settlement_report_auto_process or False
            vals['auto_send_invoice']=self.amz_auto_send_invoice or False
            vals['auto_send_refund']=self.amz_auto_send_refund or False            
            vals['create_new_product']=self.amz_create_new_product or False
            vals['order_auto_import'] = self.amz_order_auto_import or False
            vals['order_auto_import_xml_or_flat']=self.amz_order_auto_import_xml_or_flat or False
            vals['import_shipped_fbm_orders']=self.amz_import_shipped_fbm_orders or False                       
            vals['auto_process_sale_order_report']=self.amz_auto_process_sale_order_report or False       
            vals['create_sale_order_from_flat_or_xml_report']=self.amz_create_sale_order_from_flat_or_xml_report or False
            vals['is_another_soft_create_fbm_reports']=self.amz_is_another_soft_create_fbm_reports or False
            vals['global_channel_id']= self.amz_global_channel_id and self.amz_global_channel_id.id or False
            
            """added by Dhruvi"""
            vals['shipment_charge_product_id'] = self.amz_shipment_charge_product_id and self.amz_shipment_charge_product_id.id or False
            vals['gift_wrapper_product_id'] = self.amz_gift_wrapper_product_id and self.amz_gift_wrapper_product_id.id or False
            vals['promotion_discount_product_id'] = self.amz_promotion_discount_product_id and self.amz_promotion_discount_product_id.id or False
            vals['ship_discount_product_id'] = self.amz_ship_discount_product_id and self.amz_ship_discount_product_id.id or False
            vals['order_prefix']=self.amz_order_prefix and self.amz_order_prefix or False
            vals['is_default_odoo_sequence_in_sales_order']=self.is_default_odoo_sequence_in_sales_order_fbm or False
            vals['auto_create_return_picking'] = self.amz_auto_create_return_picking or False
            vals['auto_create_refund'] = self.amz_auto_create_refund or False
            vals['payment_term_id'] = self.amz_payment_term_id and self.amz_payment_term_id.id or False 
            vals['condition'] = self.amz_condition or 'New'
            vals['auto_workflow_id'] = self.amz_auto_workflow_id and self.amz_auto_workflow_id.id or False
            #vals['company_for_amazon_id'] = self.amz_seller_id.company_id and self.amz_seller_id.company_id.id or False
            vals['company_id']= self.amz_seller_id.company_id and self.amz_seller_id.company_id.id or False
            
            #added by dhaval
            vals['import_shipped_fbm_orders_date']=self.amz_import_shipped_fbm_orders_date or False
            vals['last_import_fbm_order_days']=self.amz_last_import_fbm_order_days or False
            if not self.amz_seller_id.order_last_sync_on:
                vals['order_last_sync_on']=self.amz_import_shipped_fbm_orders_date or False
            
            self.setup_amz_order_import_cron(self.amz_seller_id)
            self.setup_amz_order_import_xml_or_flat_cron(self.amz_seller_id)
            self.setup_xml_or_flat_report_process_cron(self.amz_seller_id)            
            self.amz_seller_id.write(vals)
            self.setup_amz_order_update_cron(self.amz_seller_id)
            self.setup_amz_inventory_export_cron(self.amz_seller_id)
            self.setup_amz_settlement_report_create_cron(self.amz_seller_id)
            self.setup_amz_settlement_report_process_cron(self.amz_seller_id)
            self.send_amz_invoice_via_email_seller_wise(self.amz_seller_id)
            self.send_amz_refund_via_email_seller_wise(self.amz_seller_id)
            ctx.update({'default_seller_id': self.amz_seller_id.id})            
        if res and ctx:
            res['context']=ctx
            res['params']={'seller_id':self.amz_seller_id and self.amz_seller_id.id,'instance_id': instance and instance.id or False}
        return res
    
    @api.multi
    def update_user_groups_ept(self,allow_package_group):
        group=self.sudo().env.ref('stock.group_tracking_lot')
        amazon_user_group=self.sudo().env.ref('amazon_ept.group_amazon_user_ept')
        if allow_package_group:
            if group.id not in amazon_user_group.implied_ids.ids: 
                amazon_user_group.sudo().write({'implied_ids':[(4,group.id)]})
        return True
    @api.multi   
    def setup_amz_inventory_export_cron(self,seller):
        if self.amz_stock_auto_export:
            cron_exist = self.env.ref('amazon_ept.ir_cron_auto_export_inventory_seller_%d'%(seller.id),raise_if_not_found=False)
            vals = {'active' : True,
                    'interval_number':self.amz_inventory_export_interval_number,
                    'interval_type':self.amz_inventory_export_interval_type,
                    'nextcall':self.amz_inventory_export_next_execution,
                    'user_id':self.amz_inventory_export_user_id.id,
                    'code':"model.auto_export_inventory_ept({'seller_id':%d})"%(seller.id)}
            if cron_exist:
                cron_exist.write(vals)
            else:
                export_stock_cron = self.env.ref('amazon_ept.ir_cron_auto_export_inventory',raise_if_not_found=False)
                if not export_stock_cron:
                    raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                
                name = 'FBM-'+seller.name + ' : Auto Export Inventory'
                vals.update({'name':name})
                new_cron = export_stock_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'amazon_ept',
                                                  'name':'ir_cron_auto_export_inventory_seller_%d'%(seller.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            cron_exist = self.env.ref('amazon_ept.ir_cron_auto_export_inventory_seller_%d'%(seller.id),raise_if_not_found=False)
            if cron_exist:
                cron_exist.write({'active':False})        
        return True
    
    @api.multi   
    def setup_amz_order_import_cron(self,seller):
        if self.amz_order_auto_import:
            cron_exist = self.env.ref('amazon_ept.ir_cron_import_amazon_orders_seller_%d'%(seller.id),raise_if_not_found=False)
            vals = {
                    'active' : True,
                    'interval_number':self.amz_order_import_interval_number,
                    'interval_type':self.amz_order_import_interval_type,
                    'nextcall':self.amz_order_import_next_execution,
                    'user_id':self.amz_order_import_user_id.id,                    
                    'code':"model.auto_import_sale_order_ept({'seller_id':%d})"%(seller.id)}                    
            if cron_exist:
                cron_exist.write(vals)
            else:
                import_order_cron = self.env.ref('amazon_ept.ir_cron_import_amazon_orders',raise_if_not_found=False)
                if not import_order_cron:
                    raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                
                name = 'FBM-'+seller.name + ' : Import Amazon Orders'
                vals.update({'name' : name})
                new_cron = import_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'amazon_ept',
                                                  'name':'ir_cron_import_amazon_orders_seller_%d'%(seller.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })     
                
        else:
            cron_exist = self.env.ref('amazon_ept.ir_cron_import_amazon_orders_seller_%d'%(seller.id),raise_if_not_found=False)
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    
    @api.multi   
    def setup_amz_order_import_xml_or_flat_cron(self,seller):
        if self.amz_order_auto_import_xml_or_flat and self.amz_create_sale_order_from_flat_or_xml_report!='api':
            cron_exist = self.env.ref('amazon_ept.ir_cron_xml_or_flat_import_amazon_orders_seller_%d'%(seller.id),raise_if_not_found=False)
            vals = {
                    'active' : True,
                    'interval_number':self.amz_order_auto_import_xml_or_flat_interval_number,
                    'interval_type':self.amz_order_auto_import_xml_or_flat_interval_type,
                    'nextcall':self.amz_order_auto_import_xml_or_flat_next_execution,
                    'user_id':self.amz_order_auto_import_xml_or_flat_user_id.id,
                    'code':"model.auto_import_xml_or_flat_sale_order_ept({'seller_id':%d})"%(seller.id)}
            if cron_exist:
                cron_exist.write(vals)
            else:
                import_order_cron = self.env.ref('amazon_ept.ir_cron_xml_or_flat_import_amazon_orders',raise_if_not_found=False)
                if not import_order_cron:
                    raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                
                name = 'FBM-'+seller.name + ' : Import Amazon Orders By Report'
                vals.update({'name' : name})
                new_cron = import_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'amazon_ept',
                                                  'name':'ir_cron_xml_or_flat_import_amazon_orders_seller_%d'%(seller.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        
                
        else:
            cron_exist = self.env.ref('amazon_ept.ir_cron_xml_or_flat_import_amazon_orders_seller_%d'%(seller.id),raise_if_not_found=False)
            if cron_exist:
                cron_exist.write({'active':False})
        return True
    @api.multi   
    def setup_amz_order_update_cron(self,seller):
        if self.amz_order_auto_update:
            cron_exist = self.env.ref('amazon_ept.ir_cron_auto_update_order_status_seller_%d'%(seller.id),raise_if_not_found=False)
#             nextcall = datetime.now()
#             nextcall += _intervalTypes[self.order_update_interval_type](self.order_update_interval_number)
            vals = {'active' : True,
                    'interval_number':self.amz_order_update_interval_number,
                    'interval_type':self.amz_order_update_interval_type,
                    'nextcall':self.amz_order_update_next_execution,
                    'user_id':self.amz_order_update_user_id.id,
                    'code':"model.auto_update_order_status_ept({'seller_id':%d})"%(seller.id)}
            if cron_exist:
                #vals.update({'name' : cron_exist.name})
                cron_exist.write(vals)
            else:
                update_order_cron = self.env.ref('amazon_ept.ir_cron_auto_update_order_status',raise_if_not_found=False)
                if not update_order_cron:
                    raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                
                name = 'FBM-'+seller.name + ' : Update Order Status'
                vals.update({'name' : name}) 
                new_cron = update_order_cron.copy(default=vals)
                self.env['ir.model.data'].create({'module':'amazon_ept',
                                                  'name':'ir_cron_auto_update_order_status_seller_%d'%(seller.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            cron_exist = self.env.ref('amazon_ept.ir_cron_auto_update_order_status_seller_%d'%(seller.id),raise_if_not_found=False)
            if cron_exist:
                cron_exist.write({'active':False})
        return True            
            
    @api.multi   
    def setup_amz_settlement_report_create_cron(self,seller):
        if self.amz_settlement_report_auto_create:
            cron_exist = self.env.ref('amazon_ept.ir_cron_auto_import_settlement_report_seller_%d'%(seller.id),raise_if_not_found=False)
            vals = {'active' : True,
                    'interval_number':self.amz_settlement_report_create_interval_number,
                    'interval_type':self.amz_settlement_report_create_interval_type,
                    'nextcall':self.amz_settlement_report_create_next_execution,
                    'user_id':self.amz_settlement_report_create_user_id.id,
                    'code':"model.auto_import_settlement_report({'seller_id':%d})"%(seller.id)}
                    
            if cron_exist:
                cron_exist.write(vals)
            else:
                cron_exist = self.env.ref('amazon_ept.ir_cron_auto_import_settlement_report',raise_if_not_found=False)
                if not cron_exist:
                    raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                
                name = 'FBM-'+seller.name + ' : Import Settlement Report'
                vals.update({'name' : name}) 
                new_cron = cron_exist.copy(default=vals)
                self.env['ir.model.data'].create({'module':'amazon_ept',
                                                  'name':'ir_cron_auto_import_settlement_report_seller_%d'%(seller.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            cron_exist = self.env.ref('amazon_ept.ir_cron_auto_import_settlement_report_seller_%d'%(seller.id),raise_if_not_found=False)
            if cron_exist:
                cron_exist.write({'active':False})
        return True            
    @api.multi   
    def setup_amz_settlement_report_process_cron(self,seller):
        if self.amz_settlement_report_auto_process:
            cron_exist = self.env.ref('amazon_ept.ir_cron_auto_process_settlement_report_seller_%d'%(seller.id),raise_if_not_found=False)
            vals = {'active' : True,
                    'interval_number':self.amz_settlement_report_process_interval_number,
                    'interval_type':self.amz_settlement_report_process_interval_type,
                    'nextcall':self.amz_settlement_report_process_next_execution,
                    'user_id':self.amz_settlement_report_process_user_id.id,                    
                    'code':"model.auto_process_settlement_report({'seller_id':%d})"%(seller.id)}
                    
            if cron_exist:
                cron_exist.write(vals)
            else:
                cron_exist = self.env.ref('amazon_ept.ir_cron_auto_process_settlement_report',raise_if_not_found=False)
                if not cron_exist:
                    raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                
                name = 'FBM-'+seller.name + ' : Process Settlement Report'
                vals.update({'name' : name}) 
                new_cron = cron_exist.copy(default=vals)
                self.env['ir.model.data'].create({'module':'amazon_ept',
                                                  'name':'ir_cron_auto_process_settlement_report_seller_%d'%(seller.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            cron_exist = self.env.ref('amazon_ept.ir_cron_auto_process_settlement_report_seller_%d'%(seller.id),raise_if_not_found=False)
            if cron_exist:
                cron_exist.write({'active':False})
        return True            

    @api.multi   
    def send_amz_invoice_via_email_seller_wise(self,seller):
        if self.amz_auto_send_invoice:
            cron_exist = self.env.ref('amazon_ept.ir_cron_send_amazon_invoice_via_email_seller_%d'%(seller.id),raise_if_not_found=False)
            vals = {'active' : True,
                    'interval_number':self.amz_auto_send_invoice_interval_number,
                    'interval_type':self.amz_auto_send_invoice_process_interval_type,
                    'nextcall':self.amz_auto_send_invoice_next_execution,
                    'user_id':self.amz_auto_send_invoice_user_id.id,
                    'code':"model.send_amazon_invoice_via_email({'seller_id':%d})"%(seller.id)
                    }                    
            if cron_exist:
                cron_exist.write(vals)
            else:
                cron_exist = self.env.ref('amazon_ept.ir_cron_send_amazon_invoice_via_email',raise_if_not_found=False)
                if not cron_exist:
                    raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                
                name = 'FBM-'+seller.name + ' : Invoice Send By Email'
                vals.update({'name' : name}) 
                new_cron = cron_exist.copy(default=vals)
                self.env['ir.model.data'].create({'module':'amazon_ept',
                                                  'name':'ir_cron_send_amazon_invoice_via_email_seller_%d'%(seller.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            cron_exist = self.env.ref('amazon_ept.ir_cron_send_amazon_invoice_via_email_seller_%d'%(seller.id),raise_if_not_found=False)
            if cron_exist:
                cron_exist.write({'active':False})
        return True            

    @api.multi   
    def send_amz_refund_via_email_seller_wise(self,seller):
        if self.amz_auto_send_refund:
            cron_exist = self.env.ref('amazon_ept.ir_cron_send_amazon_refund_via_email_seller_%d'%(seller.id),raise_if_not_found=False)
            vals = {'active' : True,
                    'interval_number':self.amz_auto_send_refund_interval_number,
                    'interval_type':self.amz_auto_send_refund_process_interval_type,
                    'nextcall':self.amz_auto_send_refund_next_execution,
                    'user_id':self.amz_auto_send_refund_user_id.id,
                    'code':"model.send_amazon_refund_via_email({'seller_id':%d})"%(seller.id)                   
                    }                    
            if cron_exist:
                cron_exist.write(vals)
            else:
                cron_exist = self.env.ref('amazon_ept.ir_cron_send_amazon_refund_via_email',raise_if_not_found=False)
                if not cron_exist:
                    raise Warning('Core settings of Amazon are deleted, please upgrade Amazon module to back this settings.')
                
                name = 'FBM-'+seller.name + ' : refund Send By Email'
                vals.update({'name' : name}) 
                new_cron = cron_exist.copy(default=vals)
                self.env['ir.model.data'].create({'module':'amazon_ept',
                                                  'name':'ir_cron_send_amazon_refund_via_email_seller_%d'%(seller.id),
                                                  'model': 'ir.cron',
                                                  'res_id' : new_cron.id,
                                                  'noupdate' : True
                                                  })
        else:
            cron_exist = self.env.ref('amazon_ept.ir_cron_send_amazon_refund_via_email_seller_%d'%(seller.id),raise_if_not_found=False)
            if cron_exist:
                cron_exist.write({'active':False})
        return True  
 
          
