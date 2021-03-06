# -*- coding: utf-8 -*-
import json
import ast

import requests
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError
from dateutil.parser import parse
import datetime
import base64

import logging

_logger = logging.getLogger(__name__)

_SHIPSTATION_LIST_ORDER = "https://ssapi.shipstation.com/orders?orderNumber=%s"

_SHIPSTATION_CANCEL_ORDER = "https://ssapi.shipstation.com/orders/%s"

_3PL_DOMAIN = 'http://secure-wms.com/%s'
_3PL_PATHS = {
    'auth': 'AuthServer/api/Token',
    'orders': 'orders'
}


class CenitSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    bm_id = fields.Char(string=_('Backmarket id'))
    bm_state = fields.Integer(string=_('Backmarket Orderline State'))


class CenitSaleOrder(models.Model):
    _inherit = "sale.order"

    bm_id = fields.Char(string=_('Backmarket ID'))
    bm_state = fields.Integer(string=_('Backmarket Order State'))
    shipstation_id = fields.Char(string=_('Shispstation ID'))

    # @api.multi
    # def action_confirm(self):
    #     try:
    #         config_carrier_product_manager = self.env['cenit.wireless.carrier.product']
    #         order_line_manager = self.env['sale.order.line']
    #         currency_manager = self.env['res.currency']
    #         import datetime
    #         for order in self:
    #             if order.carrier_id:
    #                 carrier_product = config_carrier_product_manager.search([('odoo_carrier','=',order.carrier_id.id)])
    #                 product = carrier_product.product
    #
    #                 temp_dict = {
    #                     'bm_id': 'SHPSERV-%s'%(str(datetime.datetime.now())),
    #                     'order_id': order.id,
    #                     'name': product.product_tmpl_id.name if product else '',
    #                     'price_unit': product.lst_price,
    #                     'state': 'draft',
    #                     'bm_state': 2,
    #                     'product_id': product.id if product else None,
    #                     'product_uom': product.product_tmpl_id.uom_id.id if product else None,
    #                     'product_uom_qty': 1,
    #                     'customer_lead': 0,  #
    #                     'create_date': datetime.datetime.now(),
    #                     'currency_id': currency_manager.search([('name', '=', 'USD')], limit=1).id,
    #                     'display_type': '' if product else 'line_section'
    #                 }
    #                 order_line_manager.create(temp_dict)
    #     except Exception:
    #         pass
    #
    #     res = super(CenitSaleOrder, self).action_confirm()
    #     return res

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

        order_temp = order[0]
        if order_temp:
            partner_manager = self.env['res.partner']
            partner_title_manager = self.env['res.partner.title']
            currency_manager = self.env['res.currency']
            country_manager = self.env['res.country']
            product_manager = self.env['product.product']
            order_manager = self.env['sale.order']
            order_line_manager = self.env['sale.order.line']
            carrier_manager = self.env['delivery.carrier']
            state_manager = self.env['res.country.state']

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

                try:
                    state = state_manager.search([('code','=', order_temp['billing_address'].get('state_or_province')), ('country_id', '=', country.id)], limit=1)
                except Exception:
                    state = state_manager.search([], limit=1)

                partner_insert_dict = {
                    'name': '%s %s'%(order_temp['billing_address'].get('first_name'),order_temp['billing_address'].get('last_name')),
                    'type': 'contact',
                    'title': temp_title.id,
                    'street': order_temp['billing_address'].get('street', ''),
                    'street2': order_temp['billing_address'].get('street2', ''),
                    'city': order_temp['billing_address'].get('city', ''),
                    'country_id': country.id,
                    'state_id':state.id,
                    'zip': order_temp['billing_address'].get('postal_code', ''),
                    'phone': order_temp['billing_address'].get('phone', ''),
                    'email': order_temp['billing_address'].get('email', '')
                }

                bm_partner = partner_manager.create(partner_insert_dict)

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

                try:
                    state = state_manager.search([('code','=', order_temp['shipping_address'].get('state_or_province')), ('country_id', '=', country.id)], limit=1)
                except Exception:
                    state = state_manager.search([], limit=1)

                partner_insert_dict = {
                    'name': '%s %s'%(order_temp['shipping_address'].get('first_name'),order_temp['shipping_address'].get('last_name')),
                    'type': 'contact',
                    'title': temp_title.id,
                    'street': order_temp['shipping_address'].get('street', ''),
                    'street2': order_temp['shipping_address'].get('street2', ''),
                    'city': order_temp['shipping_address'].get('city', ''),
                    'country_id': country.id,
                    'state_id': state.id,
                    'zip': order_temp['shipping_address'].get('postal_code', ''),
                    'phone': order_temp['shipping_address'].get('phone', ''),
                    'email': order_temp['shipping_address'].get('email', ''),
                    'parent_id': bm_partner.id
                }

                partner_shipping = partner_manager.create(partner_insert_dict)

                partner_update = {
                    'street': order_temp['shipping_address'].get('street', ''),
                    'street2': order_temp['shipping_address'].get('street2', ''),
                    'city': order_temp['shipping_address'].get('city', ''),
                    'country_id': country.id,
                    'state_id': state.id,
                    'zip': order_temp['shipping_address'].get('postal_code', ''),
                }

                partner_shipping.write(partner_update)

            else:
                try:
                    country = country_manager.search([('code','=', order_temp['shipping_address'].get('country'))], limit=1)
                except Exception:
                    country = country_manager.search([], limit=1)

                try:
                    state = state_manager.search([('code','=', order_temp['shipping_address'].get('state_or_province')), ('country_id', '=', country.id)], limit=1)
                except Exception:
                    state = state_manager.search([], limit=1)

                partner_update= {
                    'street': order_temp['shipping_address'].get('street', ''),
                    'street2': order_temp['shipping_address'].get('street2', ''),
                    'city': order_temp['shipping_address'].get('city', ''),
                    'country_id': country.id,
                    'state_id': state.id,
                    'zip': order_temp['shipping_address'].get('postal_code', ''),
                }
                partner_shipping.write(partner_update)

            #Shipping method management
            try:
                shipper = carrier_manager.search([('name','=','FedEX 2 Day')],limit=1)
                if 'shipper' in order_temp.keys() and 'usps' in order_temp['shipper'].lower():
                    shipper = carrier_manager.search([('name', '=', 'USPS Priority Mail')], limit=1)
            except Exception:
                shipper = None

            #Creating the order
            order_insert_dict = {
                'name': 'BM%s' % (order_temp.get('bm_id')),
                'origin': 'Backmarket order %s' % (order_temp.get('bm_id')),
                'state': 'draft',
                'bm_state': 1,
                'date_order': parse(order_temp.get('date_creation').split('T')[0]) if order_temp.get(
                    'date_creation') else datetime.datetime.now(),
                'validity_date': parse(order_temp.get('date_modification').split('T')[0]) if order_temp.get(
                    'date_modification') else datetime.datetime.now(),
                'create_date': parse(order_temp['date_creation'].split('T')[0]) if order_temp[
                    'date_creation'] else datetime.datetime.now(),
                'confirmation_date': datetime.datetime.now(),
                'partner_id': partner_shipping.id,
                'partner_invoice_id': bm_partner.id,
                'partner_shipping_id': partner_shipping.id,
                # 'currency_id': currency_manager.search([('name','=',order_temp['currency'])], limit=1).id if order_temp['currency'] else currency_manager.search([('name','=','USD')], limit=1).id,
                'pricelist_id': self.env['product.pricelist'].search(
                    [('name', '=', 'Public Pricelist'), ('active', '=', True)], limit=1).id,
                'bm_id': order_temp.get('bm_id')
            }

            if shipper:
                order_insert_dict["carrier_id"] = shipper.id


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
                    'price_unit': float(orderline.get('price'))/float(orderline.get('quantity')),
                    'state': 'draft',
                    'bm_state': 2,
                    'product_id': product.id if product else None,
                    'product_uom': product.product_tmpl_id.uom_id.id if product else None,
                    'product_uom_qty': orderline.get('quantity'),
                    'customer_lead': 0, #
                    'create_date': parse(orderline.get('date_creation').split('T')[0]) if orderline.get('date_creation') else datetime.datetime.now(),
                    'currency_id': currency_manager.search([('name','=',orderline.get('currency'))], limit=1).id if orderline.get('currency') else currency_manager.search([('name','=','USD')], limit=1).id,
                    'display_type': '' if product else 'line_section'
                }
                order_line_manager.create(ol_dict)

            #confirm the order and this method also generate the stock picking and sends the order to Shipstation
            new_order.action_confirm()

            # Updated BM product qty
            for sku in skus:
                product = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
                try:
                    product.update_bm_quantity()
                except Exception as ex:
                    continue

            return {'success': True, 'message': 'Order created successfully', 'order': {'order_id': new_order.name, 'skus': skus}, 'operation_type': 'create_order'}
        else:
            return {'success': False, 'message': 'Empty order', 'operation_type': 'create_order'}

    @api.model
    def cancel_backmarket_order(self, order_id):

        try:
            order = self.env['sale.order'].search([('bm_id', '=', order_id)], limit=1)
            order.action_cancel()
            return {'success': True, 'message': "The order with BM id %s was cancelled successfully" % order_id, 'operation_type': 'cancel_order'}
        except Exception as error:
            return {'success': False, 'message': error, 'operation_type': 'cancel_order'}

    @api.multi
    def action_confirm(self):
        result = super(CenitSaleOrder, self).action_confirm()
        self._send_order_Shipstation()
        return result

    @api.multi
    def action_cancel(self):
        result = super(CenitSaleOrder, self).action_cancel()
        self._cancel_order_Shipstation()
        return result

    @api.multi
    def _send_order_Shipstation(self):

        url = "https://ssapi.shipstation.com/orders/createorder"
        API_KEY = self.env['ir.config_parameter'].get_param('odoo_cenit.wireless.shipstation_api_key')
        API_SECRET = self.env['ir.config_parameter'].get_param('odoo_cenit.wireless.shipstation_api_secret')

        try:
            payload = {
                "orderNumber": self.name,
                "orderStatus": "awaiting_shipment",
                "orderDate": self.date_order.strftime('%Y-%m-%d %H:%M:%S'),
                "customerEmail": self.partner_id.email,
                "shipTo": {
                    "name": self.partner_shipping_id.name,
                    "street1": self.partner_shipping_id.street,
                    "city": self.partner_shipping_id.city,
                    "state": self.partner_shipping_id.state_id.name,
                    "country": self.partner_shipping_id.country_id.code,
                    "phone": self.partner_shipping_id.mobile if self.partner_shipping_id.mobile else self.partner_shipping_id.phone,
                    "postalCode": self.partner_shipping_id.zip
                },
                "billTo": {
                    "name": self.partner_invoice_id.name,
                    "street1": self.partner_invoice_id.street,
                    "city": self.partner_invoice_id.city,
                    "state": self.partner_invoice_id.state_id.name,

                    "country": self.partner_invoice_id.country_id.code,
                    "phone": self.partner_invoice_id.mobile if self.partner_invoice_id.mobile else self.partner_invoice_id.phone,
                    "postalCode": self.partner_invoice_id.zip
                },
                "items": [{"sku": orderline.product_id.default_code, "name": orderline.product_id.name,
                           "quantity": int(orderline.product_uom_qty), "unitPrice": orderline.price_unit} for orderline in
                          self.order_line]
            }

            headers = {
                'Host': 'ssapi.shipstation.com',
                'Content-Type': 'application/json'
            }

            response = requests.post(url, headers=headers, data=json.dumps(payload), auth=(API_KEY, API_SECRET))
            if 200 <= response.status_code < 300:
                data = response.json()
                self.write({'shipstation_id': data.get('orderId')})
                _logger.info("The order %s was created/updated in shipstation successfuly" % self.name)
            if 400 <= response.status_code < 500:
                _logger.warning("Error trying to connect to Shipstation's API")

        except Exception as error:
            _logger.info(error.args[0])

    @api.multi
    def _cancel_order_Shipstation(self):
        url = "https://ssapi.shipstation.com/orders/%s"
        API_KEY = self.env['ir.config_parameter'].get_param('odoo_cenit.wireless.shipstation_api_key')
        API_SECRET = self.env['ir.config_parameter'].get_param('odoo_cenit.wireless.shipstation_api_secret')

        headers = {
            'Host': 'ssapi.shipstation.com',
        }

        for order in self:
            response = requests.delete(url % order.shipstation_id, headers=headers, data={}, auth=(API_KEY, API_SECRET))
            if 400 <= response.status_code < 500:
                _logger.warning("Error trying to connect to Shipstation's API")

    def _send_order_3PL(self):
        # send order to 3PL
        try:
            # Authentication
            _3pl_client_id = self.env["ir.config_parameter"].get_param("odoo_cenit.wireless._3pl_client_id",
                                                                       default=None),
            _3pl_client_secret = self.env["ir.config_parameter"].get_param("odoo_cenit.wireless._3pl_client_secret",
                                                                           default=None),
            _3pl_costumer_id = self.env["ir.config_parameter"].get_param("odoo_cenit.wireless._3pl_costumer_id",
                                                                         default=None),
            _3pl_facility_id = self.env["ir.config_parameter"].get_param("odoo_cenit.wireless._3pl_facility_id",
                                                                         default=None),
            _3pl_tpl_guid = self.env["ir.config_parameter"].get_param("odoo_cenit.wireless._3pl_tpl_guid",
                                                                      default=None),
            _3pl_userlogin_id = self.env["ir.config_parameter"].get_param("odoo_cenit.wireless._3pl_userlogin_id",
                                                                          default=None)

            payload = {
                "grant_type": "client_credentials",
                "tpl": "{%s}" % _3pl_tpl_guid,
                "user_login_id": "%s" % _3pl_userlogin_id
            }
            url = _3PL_DOMAIN % _3PL_PATHS['auth']
            response = requests.post(url, auth=(''.join(_3pl_client_id), ''.join(_3pl_client_secret)), json=payload)
            auth = response.json()

            # Sending the order
            payload = {
                "customerIdentifier": {
                    "id": ''.join(_3pl_costumer_id)
                },
                "facilityIdentifier": {
                    "id": ''.join(_3pl_facility_id)
                },
                "referenceNum": self.name,
                "billingCode": "Prepaid",
                "routingInfo": {
                    "carrier": self.carrier_id.name if self.carrier_id else 'USPS',
                    "mode": " Priority Mail"  # We need to ask about this field
                },
                "shipTo": {
                    "name": self.partner_shipping_id.name,
                    "address1": self.partner_shipping_id.street,
                    "address2": self.partner_shipping_id.street2 if self.partner_shipping_id.street2 else '',
                    "city": self.partner_shipping_id.city,
                    "state": self.partner_shipping_id.state_id.name,
                    "zip": self.partner_shipping_id.zip,
                    "country": self.partner_shipping_id.country_id.code
                },
                "billTo": {
                    "name": self.partner_invoice_id.name,
                    "address1": self.partner_invoice_id.street,
                    "address2": self.partner_invoice_id.street2 if self.partner_invoice_id.street2 else '',
                    "city": self.partner_invoice_id.city,
                    "state": self.partner_invoice_id.state_id.name,
                    "zip": self.partner_invoice_id.zip,
                    "country": self.partner_invoice_id.country_id.code
                },
                "orderItems": [{"itemIdentifier": {"sku": orderline.product_id.default_code}, "qty": int(orderline.product_uom_qty)}
                               for orderline in self.order_line]
            }

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/hal+json',
                'Authorization': 'Bearer {token}'.format(token=auth.get('access_token'))
            }
            url = _3PL_DOMAIN % _3PL_PATHS['orders']
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            if 200 <= response.status_code < 300:
                _logger.info("The order %s was created in 3PL successfuly" % self.name)

        except Exception as error:
            _logger.info(error.args[0])


class CenitProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def update_quantity(self, ids):

        try:
            listing = ids[0]
            product = self.env['product.product'].search([('default_code', '=', listing)], limit=1)
            return {"listing_id": product.default_code, "quantity": product.virtual_available}
        except Exception as exc:
            return {'success': False, 'message': exc}

    @api.model
    def update_bm_quantity(self):
        bm_url = self.env["ir.config_parameter"].get_param("odoo_cenit.wireless.bm_url", default=None)
        bm_token = self.env["ir.config_parameter"].get_param("odoo_cenit.wireless.bm_token", default=None)
        bm_user_agent = self.env["ir.config_parameter"].get_param("odoo_cenit.wireless.bm_user_agent", default=None)

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Language': 'US',
            'Authorization': 'Basic %s' % bm_token,
            'User-Agent': '%s' % bm_user_agent
        }

        try:

            url = '{bm_url}/ws/listings/detail/?sku={default_code}'.format(bm_url=bm_url, default_code=self.default_code)
            _logger.info("[GET] %s " % url)
            response = requests.get(url=url, headers=headers)
            product = response.json()

            url = '{bm_url}/ws/listings/{listing_id}'.format(bm_url=bm_url, listing_id=product.get('listing_id', ''))
            payload = {
                "quantity": self.virtual_available,
            }
            _logger.info("[POST] %s ? %s ", '%s' % url, payload)
            requests.post(url=url, headers=headers, json=payload)
        except Exception as e:
            _logger.error(e)
            raise exceptions.AccessError(_("Error trying to connect to Backmarket (%s), please check the settings integrations") % url)


class CenitStockPicking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def action_cancel(self):
        result = super(CenitStockPicking, self).action_cancel()
        # if result :
        #
        #     API_KEY = self.env['ir.config_parameter'].get_param('odoo_cenit.shipstation.key')
        #     API_SECRET = self.env['ir.config_parameter'].get_param('odoo_cenit.shipstation.secret')
        #
        #     response = requests.get(_SHIPSTATION_LIST_ORDER % self.origin, auth=(API_KEY, API_SECRET))
        #     data = json.loads(response.content)
        #
        #     for order in data.get('orders'):
        #         response = requests.delete(_SHIPSTATION_CANCEL_ORDER % order.get('orderId'), auth=(API_KEY, API_SECRET))
        #         if not response.status_code == 200:
        #             _logger.info("Order {name} Cancelled. Success: {code}, Message: {message}".format(name=self.origin,
        #                                                                                               code=data.get(
        #                                                                                                   'success'),
        #                                                                                               message=data.get(
        #                                                                                                   'message')))
        #             raise ValidationError(_("Error cancelling order %s in Shipstation" % self.origin))

        return result

    @api.model
    def create(self, vals):
        res = super(CenitStockPicking, self).create(vals)
        order = self.env['sale.order'].search([('name', '=', res.origin)], limit=1)
        # if order and res.picking_type_id.name == 'Javelin: Delivery Orders':
        #if order and 'Javelin: Delivery Orders' in str(res.picking_type_id):
        order._send_order_3PL()
        return res









