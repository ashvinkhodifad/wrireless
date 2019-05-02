from odoo import models,fields,api

class SaleOrder(models.Model):
    _inherit='sale.order'
    
    @api.multi
    def compute_total_tickets(self):
        for record in self:
            helpdesk_tickets=self.env['helpdesk.ticket'].search([('sale_id','=',record.id)])
            record.total_tickets=len(helpdesk_tickets)
    
    total_tickets=fields.Integer('Total Tickets',compute=compute_total_tickets)
    
    @api.multi
    def action_view_tickets(self):
        helpdesk_tickets=self.env['helpdesk.ticket'].search([('sale_id','=',self.id)])
        if len(helpdesk_tickets)==1:
            return {
            'name': "Ticket",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'helpdesk.ticket',
            'type': 'ir.actions.act_window',
            'res_id':helpdesk_tickets.ids[0]
            }
        else:
            return {
            'name': "Tickets",
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'helpdesk.ticket',
            'type': 'ir.actions.act_window',
            'domain':[('id','in',helpdesk_tickets.ids)]
            }