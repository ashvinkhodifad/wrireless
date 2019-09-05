# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)

class CenitSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    bm_id = fields.Char(string=_('Backmarket id'))


class CenitSaleOrder(models.Model):
    _inherit = "sale.order"

    bm_id = fields.Char(string=_('Backmarket id'))

    @api.model
    def check_order_aviablity(self, order_ids):
        return {'orders': order_ids}

    @api.model
    def save_backmarket_order_real(self, order):
        from dateutil.parser import parse
        import datetime
        if order:
            partner_manager = self.env['res.partner']
            partner_title_manager = self.env['res.partner.title']
            currency_manager = self.env['res.currency']
            product_manager = self.env['product.product']
            order_manager = self.env['sale.order']
            country_manager = self.env['res.country']

            order_partner = partner_manager.search(
                [('name', 'ilike', '%s %s' % (order['first_name'], order['last_name']))], limit=1)

            if not order_partner:
                partner_insert_dict = {
                    'name': '%s %s'%(order['billing_address']['first_name'],order['billing_address']['last_name']),
                    'type': 'contact',
                    'title': partner_title_manager.search([('name','ilike','Mr')], limit=1) if order['billing_address']['gender'] == 0 else partner_title_manager.search([('name','ilike','Miss')],limit=1),
                    'street': order['billing_address']['street'],
                    'street2': order['billing_address']['street2'],
                    'city': order['billing_address']['city'],
                    'country': country_manager.search([('code','ilike',order['billing_address']['country'].split('-')[0])], limit=1) if order['billing_address']['country'] else None,
                    'zip': order['billing_address']['postal_code'],
                    'phone': order['billing_address']['phone'],
                    'email': order['billing_address']['email']
                }

                order_partner = partner_manager.create(partner_insert_dict)

            order_insert_dict = {
                'name': 'BackMarket order' % (order['bm_id']),
                'origin': 'Backmarket order %s' % (order['bm_id']),
                'state': 'draft',
                'date_order': parse(order['date_creation']) if order[
                    'date_creation'] else datetime.datetime.now(),
                'validity_date': parse(order['date_modification']) if order[
                    'date_modification'] else datetime.datetime.now(),
                'create_date': parse(order['date_creation']) if order[
                    'date_creation'] else datetime.datetime.now(),
                'confirmation_date': datetime.datetime.now(),
                'partner_id': order_partner,
                'partner_invoice_id': order_partner,
                'partner_shipping_id': order_partner,
                'currency_id': currency_manager.search([('name','=',order['currency'])], limit=1) if order['currency'] else currency_manager.search([('name','=','USD')], limit=1),

            }

        else:
            return {'success': True, 'message': 'Order created'}

    @api.model
    def save_backmarket_order(self, order):
        _logger.info(str(order))
        return {'success': True, 'message': 'Order created'}

    @api.model
    def check_backmarket_order_status(self, bm_id):
        _logger.info(str(bm_id))
        return {'success': True, 'state': 3}
