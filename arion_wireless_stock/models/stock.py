# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def button_assign_serial(self):
        self.ensure_one()
        if self.picking_type_code == 'incoming':
            for ml in self.move_line_ids.filtered(lambda l: l.product_id.tracking != 'none'):
                ml.lot_name = self.env['ir.sequence'].next_by_code('stock.incoming.serial.lot')
