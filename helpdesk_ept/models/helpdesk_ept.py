from odoo import api, fields, models, _

class helpdesk_ept(models.Model):
    _inherit = 'helpdesk.ticket' 
    
    @api.onchange('sale_id')
    def onchange_sale_id(self):
        self.partner_id = self.sale_id.partner_id.id
        self._onchange_partner_id()
        
    sale_id = fields.Many2one("sale.order", string="Sale Order")