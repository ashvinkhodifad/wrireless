from odoo import models,fields,api

class EbayHelpDeskSupport(models.Model):
    _inherit = 'helpdesk.ticket'
    
    ebay_instance_id = fields.Many2one("ebay.instance.ept",string="Ebay Instance")
    
    @api.onchange('sale_id')
    def onchange_sale_id(self):
        res = super(EbayHelpDeskSupport,self).onchange_sale_id()
        if self.sale_id.ebay_instance_id:
            self.ebay_instance_id = self.sale_id.ebay_instance_id and self.sale_id.ebay_instance_id.id or False 
            self.team_id = self.sale_id.ebay_instance_id.helpdesk_team_id and self.sale_id.ebay_instance_id.helpdesk_team_id.id or False
        return res
    
class EbayInstanceEpt(models.Model):
    _inherit = 'ebay.instance.ept'
    
    helpdesk_team_id = fields.Many2one('helpdesk.team')
    
class EbayConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'
    
    helpdesk_team_id = fields.Many2one('helpdesk.team',string="Helpdesk Team")
    
    @api.multi
    def execute(self):
        instance = self.ebay_instance_id
        values = {}
        res = super(EbayConfiguration,self).execute()
        if instance:
            values['helpdesk_team_id'] = self.helpdesk_team_id and self.helpdesk_team_id.id or False
            instance.write(values)
        return res
    
    
    @api.onchange('ebay_instance_id')
    def onchange_ebay_instance_id(self):
        values = super(EbayConfiguration,self).onchange_ebay_instance_id()#,instance,product_ads_account
        instance = self.ebay_instance_id 
        if instance:    
            self.helpdesk_team_id = instance.helpdesk_team_id and instance.helpdesk_team_id.id or False
   
    
