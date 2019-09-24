# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)

class CenitSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    bm_id = fields.Char(string=_('Backmarket id'))
    bm_state = fields.Integer(string=_('Backmarket Orderline State'))


class CenitSaleOrder(models.Model):
    _inherit = "sale.order"

    bm_id = fields.Char(string=_('Backmarket id'))
    bm_state = fields.Integer(string=_('Backmarket Order State'))

    @api.model
    def check_backmarket_order_status(self, order_ids):
        picking_manager = self.env['stock.picking']
        orders = self.env['sale.order'].search([('bm_id', 'in', order_ids)])
        result = []
        for order in orders:
            tmp = {'bm_id': order.bm_id, 'bm_state': order.bm_state}
            ol_reults = []
            for orderline in order.order_line:
                tmp2 = {'bm_id': orderline.bm_id, 'new_state': orderline.bm_state,
                        'sku': orderline.product_id.default_code, 'tracking_number': ''}
                ol_reults.append(tmp2)
            tmp['orderlines'] = ol_reults
            result.append(tmp)

        return result


    @api.model
    def save_backmarket_order(self, order):
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
                [('name', 'ilike', '%s %s' % (order_temp['billing_address'].get('first_name'), order_temp['billing_address'].get('last_name')))], limit=1)

            partner_shipping = partner_manager.search(
                [('name', 'ilike', '%s %s' % (order_temp['shipping_address'].get('first_name'), order_temp['shipping_address'].get('last_name')))], limit=1)

            if not order_partner:
                try:
                    temp_title = partner_title_manager.search([('name','=','Mr.')], limit=1) if order_temp['billing_address'].get('gender') == 0 else partner_title_manager.search([('name','=','Miss')],limit=1)
                except Exception:
                    temp_title = partner_title_manager.search([])
                    if temp_title:
                        temp_title = temp_title[0]

                partner_insert_dict = {
                    'name': '%s %s'%(order_temp['billing_address'].get('first_name'),order_temp['billing_address'].get('last_name')),
                    'type': 'contact',
                    'title': temp_title,
                    'street': order_temp['billing_address'].get('street', ''),
                    'city': order_temp['billing_address'].get('city', ''),
                    'country': country_manager.search([('code','=', order_temp['billing_address'].get('country'))], limit=1) if order_temp['billing_address'].get('country') else None,
                    'zip': order_temp['billing_address'].get('postal_code', ''),
                    'phone': order_temp['billing_address'].get('phone', ''),
                    'email': order_temp['billing_address'].get('email', '')
                }

                order_partner = partner_manager.create(partner_insert_dict)

            #creand order
            order_insert_dict = {
                'name': 'BM%s' % (order_temp.get('bm_id')),
                'origin': 'Backmarket order %s' % (order_temp.get('bm_id')),
                'state': 'draft',
                'bm_state': 1,
                'date_order': parse(order_temp.get('date_creation')) if order_temp.get('date_creation') else datetime.datetime.now(),
                'validity_date': parse(order_temp.get('date_modification')) if order_temp.get('date_modification') else datetime.datetime.now(),
                'create_date': parse(order_temp['date_creation']) if order_temp[
                    'date_creation'] else datetime.datetime.now(),
                'confirmation_date': datetime.datetime.now(),
                'partner_id': order_partner.id,
                'partner_invoice_id': order_partner.id,
                'partner_shipping_id': partner_shipping.id if partner_shipping else order_partner.id,
                #'currency_id': currency_manager.search([('name','=',order_temp['currency'])], limit=1).id if order_temp['currency'] else currency_manager.search([('name','=','USD')], limit=1).id,
                'pricelist_id': self.env['product.pricelist'].search([('name', '=', 'Public Pricelist'), ('active', '=', True)], limit=1).id,
                'bm_id': order_temp.get('bm_id')
            }

            new_order = order_manager.create(order_insert_dict)
            for orderline in order_temp.get('orderlines') :
                product = product_manager.search([('default_code', '=', orderline['listing'])], limit=1)
                if not product:
                    # Send an email with order.bm_id and orderline.bm_id equal to order_temp['bm_id']
                    pass
                ol_dict = {
                    'bm_id': orderline.get('id'),
                    'order_id': new_order.id,
                    'name': product.product_tmpl_id.name if product else 'BackMarket orderline %s' % (orderline.get('id')),
                    'price_unit': orderline.get('price'),
                    'state': 'draft',
                    'bm_state': orderline.get('state') or 1,
                    'product_id': product if product else None,
                    'product_uom': product.product_tmpl_id.uom_id if product else None,
                    'product_uom_qty': orderline.get('quantity') if product else None,
                    'customer_lead': 0, #Esto no c lo que es pero es NOT NULL
                    'create_date': parse(orderline.get('date_creation')) if orderline.get('date_creation') else datetime.datetime.now(),
                    'currency_id': currency_manager.search([('name','=',orderline.get('currency'))], limit=1).id if orderline.get('currency') else currency_manager.search([('name','=','USD')], limit=1).id,
                    'display_type': '' if product else 'line_section'
                }
                order_line_manager.create(ol_dict)

            return {'success': True, 'message': 'Order created successfully', 'order_name': new_order.name}

        else:
            return {'success': False, 'message': 'Empty order'}
