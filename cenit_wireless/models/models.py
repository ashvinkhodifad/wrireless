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
        order_ids =[{}]
        return {'orders': order_ids}

    @api.model
    def save_backmarket_order_real(self, order):
        from dateutil.parser import parse
        import datetime
        order_temp = order[0]

        if order_temp:
            partner_manager = self.env['res.partner']
            partner_title_manager = self.env['res.partner.title']
            currency_manager = self.env['res.currency']
            country_manager = self.env['res.country']
            product_manager = self.env['product.product']
            order_manager = self.env['sale.order']
            order_line_manager = self.env['sale.order.line']

            order_partner = partner_manager.search(
                [('name', 'ilike', '%s %s' % (order_temp['billing_address']['first_name'], order_temp['billing_address']['last_name']))], limit=1)

            partner_shipping = partner_manager.search(
                [('name', 'ilike', '%s %s' % (order_temp['shipping_address']['first_name'], order_temp['shipping_address']['last_name']))], limit=1)

            if not order_partner:
                partner_insert_dict = {
                    'name': '%s %s'%(order_temp['billing_address']['first_name'],order_temp['billing_address']['last_name']),
                    'type': 'contact',
                    'title': partner_title_manager.search([('name','ilike','Mr')], limit=1) if order_temp['billing_address']['gender'] == 0 else partner_title_manager.search([('name','ilike','Miss')],limit=1),
                    'street': order_temp['billing_address']['street'],
                    'street2': order_temp['billing_address']['street2'],
                    'city': order_temp['billing_address']['city'],
                    'country': country_manager.search([('code','=', str(order_temp['billing_address']['country'].split('-')[1].upper()))], limit=1) if order_temp['billing_address']['country'] else None,
                    'zip': order_temp['billing_address']['postal_code'],
                    'phone': order_temp['billing_address']['phone'],
                    'email': order_temp['billing_address']['email']
                }

                order_partner = partner_manager.create(partner_insert_dict)

            #creand order
            order_insert_dict = {
                'name': 'BackMarket order %s' % (order_temp['bm_id']),
                'origin': 'Backmarket order %s' % (order_temp['bm_id']),
                'state': 'draft',
                'date_order': parse(order_temp['date_creation']) if order_temp[
                    'date_creation'] else datetime.datetime.now(),
                'validity_date': parse(order_temp['date_modification']) if order_temp[
                    'date_modification'] else datetime.datetime.now(),
                'create_date': parse(order_temp['date_creation']) if order_temp[
                    'date_creation'] else datetime.datetime.now(),
                'confirmation_date': datetime.datetime.now(),
                'partner_id': order_partner,
                'partner_invoice_id': order_partner,
                'partner_shipping_id': partner_shipping or order_partner,
                'currency_id': currency_manager.search([('name','=',order_temp['currency'])], limit=1) if order_temp['currency'] else currency_manager.search([('name','=','USD')], limit=1),
                'bm_id': order_temp['bm_id']
            }

            new_order = order_manager.create(order_insert_dict)
            for orderline in order_temp['orderlines'] :
                product = product_manager.search([('default_code', '=', orderline['listing'])], limit=1)
                if not product:
                    # Send an email with order.bm_id and orderline.bm_id equal order_temp['bm_id']
                    pass
                ol_dict = {
                    'bm_id': order_temp['bm_id'],
                    'order_id': new_order.id,
                    'name': product.product_tmpl_id.name if product else 'BackMarket orderline %s' % (order_temp['bm_id']),
                    'price_unit': orderline['price'],
                    'product_uom_qty': orderline['quantity'],
                    'customer_lead': 0, #Esto no c lo que es pero es NOT NULL
                    'create_date': parse(orderline['date_creation']) if orderline['date_creation'] else datetime.datetime.now(),
                    'currency_id': currency_manager.search([('name','=',orderline['currency'])], limit=1) if orderline['currency'] else currency_manager.search([('name','=','USD')], limit=1),
                    'product_id': product if product else None
                }
                order_line_manager.create(ol_dict)

            return {'success': True, 'message': 'Order created successfully', 'order_name': new_order.name}

        else:
            return {'success': False, 'message': 'Empty order'}

    @api.model
    def save_backmarket_order(self, order):
        _logger.info(str(order))
        return {'success': True, 'message': 'Order created'}

    @api.model
    def check_backmarket_order_status(self, bm_id):
        _logger.info(str(bm_id))
        return {'success': True, 'state': 3}
