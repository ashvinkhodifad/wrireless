# -*- coding: utf-8 -*-
import json

import requests
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

        orders = self.env['sale.order'].search([('bm_id', 'in', order_ids)])

        result = []
        for order in orders:
            stock_picking = self.env['stock.picking'].search([('origin', '=', order.name)], limit=1)

            if not stock_picking:
                break

            tmp = {'order_id': order.bm_id}
            ol_results = []
            for orderline in order.order_line:
                tmp2 = {'orderline_id': orderline.bm_id, 'new_state': orderline.bm_state,
                        'sku': orderline.product_id.default_code, 'tracking_number': stock_picking.carrier_tracking_ref,
                        'shipper': stock_picking.carrier_id.name}
                ol_results.append(tmp2)
            tmp['orderlines'] = ol_results
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

            order = order_manager.search([('name', '=', 'BM%s' % order_temp.get('bm_id'))], limit=1)
            if order:
                return {'success': False, 'message': 'Order BM%s already exists' % order_temp.get('bm_id')}

            bm_partner = partner_manager.search([('name', '=', 'Backmarket')], limit=1)

            if not bm_partner:
                try:
                    temp_title = partner_title_manager.search([('name','=','Miss')], limit=1) if order_temp['billing_address'].get('gender') == 0 else partner_title_manager.search([('name','=','Mister')],limit=1)
                except Exception:
                    temp_title = partner_title_manager.search([], limit=1)

                try:
                    country = country_manager.search([('code','=', order_temp['billing_address'].get('country'))], limit=1)
                except Exception:
                    country = country_manager.search([], limit=1)

                partner_insert_dict = {
                    'name': '%s %s'%(order_temp['billing_address'].get('first_name'),order_temp['billing_address'].get('last_name')),
                    'type': 'contact',
                    'title': temp_title.id,
                    'street': order_temp['billing_address'].get('street', ''),
                    'city': order_temp['billing_address'].get('city', ''),
                    'country_id': country.id,
                    'zip': order_temp['billing_address'].get('postal_code', ''),
                    'phone': order_temp['billing_address'].get('phone', ''),
                    'email': order_temp['billing_address'].get('email', '')
                }

                order_partner = partner_manager.create(partner_insert_dict)

            partner_shipping = partner_manager.search(
                [('name', 'ilike', '%s %s' % (order_temp['shipping_address'].get('first_name'), order_temp['shipping_address'].get('last_name')))], limit=1)

            if not partner_shipping:
                try:
                    temp_title = partner_title_manager.search([('name','=','Miss')], limit=1) if order_temp['shipping_address'].get('gender') == 0 else partner_title_manager.search([('name','=','Mister')],limit=1)
                except Exception:
                    temp_title = partner_title_manager.search([], limit=1)

                try:
                    country = country_manager.search([('code','=', order_temp['shipping_address'].get('country'))], limit=1)
                except Exception:
                    country = country_manager.search([], limit=1)

                partner_insert_dict = {
                    'name': '%s %s'%(order_temp['shipping_address'].get('first_name'),order_temp['shipping_address'].get('last_name')),
                    'type': 'contact',
                    'title': temp_title.id,
                    'street': order_temp['shipping_address'].get('street', ''),
                    'city': order_temp['shipping_address'].get('city', ''),
                    'country_id': country.id,
                    'zip': order_temp['shipping_address'].get('postal_code', ''),
                    'phone': order_temp['shipping_address'].get('phone', ''),
                    'email': order_temp['shipping_address'].get('email', ''),
                    'parent_id': bm_partner.id
                }

                partner_shipping = partner_manager.create(partner_insert_dict)

            #Creating the order
            order_insert_dict = {
                'name': 'BM%s' % (order_temp.get('bm_id')),
                'origin': 'Backmarket order %s' % (order_temp.get('bm_id')),
                'state': 'draft',
                'bm_state': 1,
                'date_order': parse(order_temp.get('date_creation').split('T')[0]) if order_temp.get('date_creation') else datetime.datetime.now(),
                'validity_date': parse(order_temp.get('date_modification').split('T')[0]) if order_temp.get('date_modification') else datetime.datetime.now(),
                'create_date': parse(order_temp['date_creation'].split('T')[0]) if order_temp[
                    'date_creation'] else datetime.datetime.now(),
                'confirmation_date': datetime.datetime.now(),
                'partner_id': partner_shipping.id,
                'partner_invoice_id': bm_partner.id,
                'partner_shipping_id': partner_shipping.id,
                #'currency_id': currency_manager.search([('name','=',order_temp['currency'])], limit=1).id if order_temp['currency'] else currency_manager.search([('name','=','USD')], limit=1).id,
                'pricelist_id': self.env['product.pricelist'].search([('name', '=', 'Public Pricelist'), ('active', '=', True)], limit=1).id,
                'bm_id': order_temp.get('bm_id')
            }

            new_order = order_manager.create(order_insert_dict)
            skus = []
            for orderline in order_temp.get('orderlines') :
                product = product_manager.search([('default_code', '=', orderline.get('listing'))], limit=1)
                if not product:
                    # Send an email with order.bm_id and orderline.bm_id equal to order_temp['bm_id']
                    pass

                skus.append(orderline.get('listing'))

                ol_dict = {
                    'bm_id': orderline.get('id'),
                    'order_id': new_order.id,
                    'name': product.product_tmpl_id.name if product else 'BackMarket orderline %s' % (orderline.get('id')),
                    'price_unit': orderline.get('price'),
                    'state': 'draft',
                    'bm_state': 2,
                    'product_id': product.id if product else None,
                    'product_uom': product.product_tmpl_id.uom_id.id if product else None,
                    'product_uom_qty': orderline.get('quantity') if product else None,
                    'customer_lead': 0, #
                    'create_date': parse(orderline.get('date_creation').split('T')[0]) if orderline.get('date_creation') else datetime.datetime.now(),
                    'currency_id': currency_manager.search([('name','=',orderline.get('currency'))], limit=1).id if orderline.get('currency') else currency_manager.search([('name','=','USD')], limit=1).id,
                    'display_type': '' if product else 'line_section'
                }
                order_line_manager.create(ol_dict)

            #confirm the order and this method also generate the stock picking
            new_order.action_confirm()
            return {'success': True, 'message': 'Order created successfully', 'order': {'order_id': new_order.name, 'skus': skus}}

        else:
            return {'success': False, 'message': 'Empty order'}

    @api.model
    def cancel_backmarket_order(self, order_id):

        try:
            order = self.env['sale.order'].search([('bm_id', '=', order_id)], limit=1)
            order.action_cancel()
            return {'success': True, 'message': "The order with BM id %s was cancelled successfully" % order_id}
        except Exception as error:
            return {'success': False, 'message': error}



class CenitProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def update_quantity(self, ids):

        try:
            listing = ids[0]
            product = self.env['product.template'].search([('default_code', '=', listing)])
            return {"listing_id": product.default_code, "quantity": product.qty_available}
        except Exception as exc:
            return {'success': False, 'message': exc}


