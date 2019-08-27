# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # available_kit_qty = fields.Float(string='Kit Quantity', compute='_compute_quantities')

    @api.depends(
        'product_variant_ids',
        'product_variant_ids.stock_move_ids.product_qty',
        'product_variant_ids.stock_move_ids.state',
    )
    def _compute_quantities(self):
        res = self._compute_quantities_dict()
        for template in self:
            available_kit_qty = 0
            if template.bom_ids:
                for product in template.product_variant_ids:
                    available_kit_qty += product._get_availability_kit_qty()
            template.outgoing_qty = res[template.id]['outgoing_qty']
            template.virtual_available = res[template.id]['virtual_available']
            template.incoming_qty = res[template.id]['incoming_qty']
            template.qty_available = template.bom_ids and available_kit_qty or res[template.id]['qty_available']


class ProductProduct(models.Model):
    _inherit = "product.product"

    # available_kit_qty = fields.Float(string='Kit Quantity', compute='_compute_quantities')

    def _get_availability_kit_qty(self):
        MrpBom = self.env['mrp.bom']
        bom = MrpBom._bom_find(product_tmpl=self.product_tmpl_id, product=self, company_id=self.company_id.id)
        if bom and bom.type == 'phantom':
            products = {}
            for line in bom.bom_line_ids.filtered(lambda l: l.attribute_value_ids.ids in self.attribute_value_ids.ids or not l.attribute_value_ids):
                qty = line.product_qty
                if line.product_id.id in products.keys():
                    products[line.product_id.id]['qty'] += qty
                else:
                    products.update({line.product_id.id: {'qty_available': line.product_id.qty_available, 'qty': qty}})
            possible_qty = []
            for p in products:
                possible_qty.append(int(products[p]['qty_available'] / products[p]['qty']))
            if possible_qty:
                return min(possible_qty)
            else:
                return 0.00
        else:
            return 0.00

    @api.depends('stock_move_ids.product_qty', 'stock_move_ids', 'stock_move_ids.state')
    def _compute_quantities(self):
        res = self._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self._context.get('from_date'), self._context.get('to_date'))
        for product in self:
            product.outgoing_qty = res[product.id]['outgoing_qty']
            product.incoming_qty = res[product.id]['incoming_qty']
            product.virtual_available = res[product.id]['virtual_available']
            if product.bom_ids or product.product_tmpl_id.bom_ids:
                product.qty_available = product._get_availability_kit_qty()
            else:
                product.qty_available = res[product.id]['qty_available']
