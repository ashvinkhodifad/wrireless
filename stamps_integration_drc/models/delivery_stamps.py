# -*- coding: utf-8 -*-
import re
import base64
import requests

from time import sleep

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date, datetime

from odoo.addons.stamps_integration_drc.stamps.config import StampsConfiguration
from odoo.addons.stamps_integration_drc.stamps.services import StampsService


ZIP_ZIP4 = re.compile('^[0-9]{5}(-[0-9]{4})?$')


def split_zip(zipcode):
    '''If zipcode is a ZIP+4, split it into two parts.
       Else leave it unchanged '''
    if ZIP_ZIP4.match(zipcode) and '-' in zipcode:
        return zipcode.split('-')
    else:
        return [zipcode, '']


class ProviderStamps(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('stamps', "Stamps")])
    stamps_username = fields.Char(string='Stamps User ID', groups="base.group_system")
    stamps_password = fields.Char(string='Stamps Password', groups="base.group_system")
    stamps_integration_id = fields.Char(string='Stamps Integration ID', groups="base.group_system")
    stamps_delivery_nature = fields.Selection([('domestic', 'Domestic'),
                                             ('international', 'International')],
                                            string="Delivery Nature", default='domestic', required=True)
    stamps_default_service_type = fields.Selection([('US-FC', 'USPS First-Class Mail'),
                                                 ('US-MM', 'USPS Media Mail'),
                                                 ('US-PP', 'USPS Parcel Post'),
                                                 ('US-PM', 'USPS Priority Mail'),
                                                 ('US-XM', 'USPS Priority Mail Express'),
                                                 ('US-EMI', 'USPS Priority Mail Express International'),
                                                 ('US-PMI', 'USPS Priority Mail International'),
                                                 ('US-FCI', 'USPS First Class Mail International'),
                                                 ('US-PS', 'USPS Parcel Select Ground'),
                                                 ('US-LM', 'USPS Library Mail')],
                                               string="Stamps Service Type", default='US-PS')
    stamps_label_file_type = fields.Selection([('Gif', 'GIF format'),
                                            ('Jpg', 'JPEG format'),
                                            ('Pdf','PDF format'),
                                            ('Png','PNG format'),
                                            ('Zpl', 'ZPL'),
                                            ('Epl', 'EPL printer')],
                                           string="Stamps Label File Type", default='Pdf')
    stamps_content_type = fields.Selection([('Commercial Sample', 'Commercial Sample'),
                                            ('Gift', 'Gift'),
                                            ('Document', 'Document'),
                                            ('Returned Goods', 'Returned Goods'),
                                            ('Merchandise', 'Merchandise'),
                                            ('Humanitarian Donation','Humanitarian Donation'),
                                            ('Dangerous Goods','Dangerous Goods'),
                                            ('Other','Other')],
                                           string="Stamps Content Type", default='Merchandise')
    stamps_package_name = fields.Selection([('Large Envelope or Flat', 'Large Envelope or Flat'),
                                            ('Legal Flat Rate Envelope', 'Legal Flat Rate Envelope'),
                                            ('Flat Rate Padded Envelope', 'Flat Rate Padded Envelope'),
                                            ('Package','Package'),
                                            ('Small Flat Rate Box', 'Small Flat Rate Box'),
                                            ('Flat Rate Box', 'Medium Flat Rate Box'),
                                            ('Large Flat Rate Box', 'Large Flat Rate Box'),
                                            ('Large Package','Large Package'),
                                            ('Oversized Package','Oversized Package'),
                                            ('Regional Rate Box A','Regional Rate Box A'),
                                            ('Regional Rate Box B','Regional Rate Box B'),
                                            ('Regional Rate Box C','Regional Rate Box C')],
                                            string="Stamps Priority Package", default='Package')
    stamps_transaction_id = fields.Char('Last Transaction Id')
    stamps_sample_check = fields.Boolean(string='Sample Check', default=True)


    def check_required_value(self, recipient, delivery_nature, shipper, order=False, picking=False):
        recipient_required_field = ['city', 'zip', 'state_id', 'country_id','phone']
        if not recipient.street and not recipient.street2:
            recipient_required_field.append('street')
        shipper_required_field = ['city', 'zip', 'phone', 'state_id', 'country_id']
        if not recipient.street and not recipient.street2:
            shipper_required_field.append('street')

        res = [field for field in shipper_required_field if not shipper[field]]
        if res:
            return _("The address of your company is missing or wrong (Missing field(s) :  \n %s)") % ", ".join(res).replace("_id", "")
        if shipper.country_id.code != 'US':
            return _("Please set country U.S.A in your company address, Service is only available for U.S.A")
        if not ZIP_ZIP4.match(shipper.zip):
            return _("Please enter a valid ZIP code in your Company address")
        if not self._convert_phone_number(shipper.phone):
            return _("Company phone number is invalid. Please insert a US phone number.")
        res = [field for field in recipient_required_field if not recipient[field]]
        if res:
            return _("The recipient address is missing or wrong (Missing field(s) :  \n %s)") % ", ".join(res).replace("_id", "")
        if delivery_nature == 'domestic' and not ZIP_ZIP4.match(recipient.zip):
            return _("Please enter a valid ZIP code in recipient address")
        if recipient.country_id.code == "US" and delivery_nature == 'international':
            return _("USPS International is used only to ship outside of the U.S.A. Please change the delivery method into USPS Domestic.")
        if recipient.country_id.code != "US" and delivery_nature == 'domestic':
            return _("USPS Domestic is used only to ship inside of the U.S.A. Please change the delivery method into USPS International.")
        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            tot_weight = sum([(line.product_id.weight * line.product_qty) for line in order.order_line]) or 0
            for line in order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type not in ['service', 'digital']):
                return _('The estimated price cannot be computed because the weight of your product is missing.')
        if picking:
            for move in picking.move_lines.filtered(lambda move: not move.product_id.weight):
                return _("The delivery cannot be done because the weight of your product is missing.")
        return False


    def get_rate(self, service, order=False):
        ret_val = service.create_shipping()
        ret_val.ShipDate = date.today().isoformat()
        ret_val.FromZIPCode = order.warehouse_id.partner_id.zip
        ret_val.ToZIPCode = order.partner_shipping_id.zip
        ret_val.PackageType = order.carrier_id.stamps_package_name#"Package"
        ret_val.ServiceType = order.carrier_id.stamps_default_service_type
        ret_val.ContentType = order.carrier_id.stamps_content_type
        tot_weight = (sum([(line.product_id.weight * line.product_qty) for line in order.order_line])) * 2.21 or 0
        ret_val.WeightLb = tot_weight
        rate = service.get_rates(ret_val)[0]
        ret_val.Amount = rate.Amount
        ret_val.DeliverDays = rate.DeliverDays
        ret_val.DimWeighting = rate.DimWeighting
        ret_val.Zone = rate.Zone
        ret_val.RateCategory = rate.RateCategory
        if rate.ToState:
            ret_val.ToState = rate.ToState
        add_on = service.create_add_on()
        add_on.AddOnType = "US-A-DC"
        ret_val.AddOns.AddOnV11.append(add_on)
        return ret_val

    def get_from_address(self, service, shipper):
        """Get a test 'from' address.

        :param service: Instance of the stamps service.
        """
        address = service.create_address()
        if shipper.name.strip():
            address.Company = shipper.name
        else:
            raise ValidationError('The sender name is missing.')
        address.Address1 = shipper.street
        address.Address2 = shipper.street2 or ''
        address.City = shipper.city or ''
        address.PhoneNumber = shipper.phone
        if shipper.state_id.code:
            address.State = (shipper.state_id.code).upper()
        address.ZIPCode = shipper.zip

        return service.get_address(address).Address


    def get_to_address(self, service, ship_to):
        """Get a test 'to' address.

        :param service: Instance of the stamps service.
        """
        address = service.create_address()
        if ship_to.name.strip():
            address.FullName = ship_to.name
        else:
            raise ValidationError('The recipient name is missing.')
        address.Company = ship_to.parent_id.name or ''
        address.Address1 = ship_to.street
        address.Address2 = ship_to.street2 or ''
        address.City = ship_to.city or ''
        address.PhoneNumber = ship_to.phone
        if ship_to.state_id.code:
            address.State = (ship_to.state_id.code).upper()
        address.ZIPCode = ship_to.zip
        if ship_to.apo_fpo_dpo:
            address.ZIPCodeAddOn = ship_to.zip_code_addon

        return service.get_address(address).Address

    def _convert_phone_number(self, phone):
        phone_pattern = re.compile(r'''
                # don't match beginning of string, number can start anywhere
                (\d{3})     # area code is 3 digits (e.g. '800')
                \D*         # optional separator is any number of non-digits
                (\d{3})     # trunk is 3 digits (e.g. '555')
                \D*         # optional separator
                (\d{4})     # rest of number is 4 digits (e.g. '1212')
                \D*         # optional separator
                (\d*)       # extension is optional and can be any number of digits
                $           # end of string
                ''', re.VERBOSE)
        match = phone_pattern.search(phone)
        if match:
            return ''.join(str(digits_number) for digits_number in match.groups())
        else:
            return False

    def stamps_rate_shipment(self, orders):
        res = []
        superself = self.sudo()
        if not self.prod_environment:
            prod_environment = 'testing'
        else:
            prod_environment = None
        config_proc = StampsConfiguration(integration_id=superself.stamps_integration_id,username=superself.stamps_username, password=superself.stamps_password, wsdl=prod_environment)
        service = StampsService(config_proc)
        account = service.get_account()
        for order in orders:
            check_result = self.check_required_value(order.partner_shipping_id, order.carrier_id.stamps_delivery_nature, order.warehouse_id.partner_id, order=order)
            if check_result:
                return {'success': False,
                        'price': 0.0,
                        'error_message': check_result,
                        'warning_message': False}
            rate = self.get_rate(service, order)
            if order.currency_id.name == 'USD':
                price = float(rate['Amount'])
            else:
                quote_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
                price = quote_currency.compute(float(rate['Amount']), order.currency_id)
        return {'success': True,
                'price': price,
                'error_message': False,
                'warning_message': False}

    def stamps_send_shipping(self, pickings):
        res = []
        superself = self.sudo()
        customs = None
        if not self.prod_environment:
            prod_environment = 'testing'
            sample = self.stamps_sample_check
        else:
            prod_environment = None
            sample = False
        config_proc = StampsConfiguration(integration_id=superself.stamps_integration_id,username=superself.stamps_username, password=superself.stamps_password, wsdl=prod_environment)
        service = StampsService(config_proc)
        account = service.get_account()
        for picking in pickings:
            check_result= self.check_required_value(picking.partner_id, picking.carrier_id.stamps_delivery_nature, picking.picking_type_id.warehouse_id.partner_id, picking=picking)
            if check_result:
                raise ValidationError(check_result)
            ret_val = service.create_shipping()
            ret_val.ShipDate = date.today().isoformat()
            ret_val.FromZIPCode = picking.picking_type_id.warehouse_id.partner_id.zip
            ret_val.ToZIPCode = picking.partner_id.zip
            ret_val.ToCountry = picking.partner_id.country_id.code
            ret_val.PackageType = picking.carrier_id.stamps_package_name#"Package"
            ret_val.ServiceType = picking.carrier_id.stamps_default_service_type
            ret_val.ContentType = picking.carrier_id.stamps_content_type
            tot_weight = picking.shipping_weight * 2.21 or 0
            ret_val.WeightLb = tot_weight
            ret_val.WeightOz = 0
            add_on = service.create_add_on()
            add_on.AddOnType = "US-A-DC"
            ret_val.AddOns.AddOnV11.append(add_on)
            sale_order = self.env['sale.order'].search([('name','=',picking.origin)])
            if sale_order.client_order_ref:
                memo = 'Customer Reference1: ' + picking.origin + '\nCustomer Reference2: ' + sale_order.client_order_ref
            else:
                memo = 'Customer Reference1: ' + picking.origin + '\nCustomer Reference2: ' + ' - '

            from_address = self.get_from_address(service, picking.picking_type_id.warehouse_id.partner_id)
            to_address = self.get_to_address(service, picking.partner_id)

            if picking.package_ids:
                carrier_tracking_ref = ''
                stamps_transaction_id = ''
                labels = []
                for package in picking.package_ids:
                    tot_weight = package.shipping_weight * 2.21 or 0
                    ret_val.WeightLb = tot_weight
                    ret_val.WeightOz = 0
                    try:
                        rate = service.get_rates(ret_val)[0]
                    except Exception as e:
                        raise ValidationError(e)
                    ret_val.Amount = rate.Amount
                    ret_val.DeliverDays = rate.DeliverDays
                    ret_val.DimWeighting = rate.DimWeighting
                    ret_val.Zone = rate.Zone
                    ret_val.RateCategory = rate.RateCategory
                    ret_val.ToState = rate.ToState
                    if picking.partner_id.apo_fpo_dpo:
                        products = [line.product_id.name for line in picking.move_lines if line.quantity_done >= line.product_uom_qty]
                        ret_val.DeclaredValue = rate.Amount
                        customs = service.create_customs()
                        customs.ContentType.value = picking.carrier_id.stamps_content_type
                        custom_line = service.create_customs_lines()
                        custom_line.Description = ",".join(products)
                        custom_line.Quantity = sum([line.quantity_done for line in picking.move_lines])
                        custom_line.Value = rate.Amount
                        custom_line.WeightLb = tot_weight
                        custom_line.CountryOfOrigin = picking.picking_type_id.warehouse_id.partner_id.country_id.code
                        customs.CustomsLines.CustomsLine.append(custom_line)
                        ret_val.PrintLayout = 'Normal4X6CN22Thermal'
                    transaction_id = str(picking.name) + str(datetime.now().isoformat())
                    label = service.get_label(from_address, to_address, ret_val, transaction_id=transaction_id, sample=sample, image_type=picking.carrier_id.stamps_label_file_type, memo=memo, customs=customs)
                    if label:
                        currency_order = picking.sale_id.currency_id
                        if not currency_order:
                            currency_order = picking.company_id.currency_id

                        # USPS always returns prices in USD
                        if currency_order.name == "USD":
                            price = float(label.Rate.Amount)
                        else:
                            quote_currency = self.env['res.currency'].search([('name', '=', "USD")], limit=1)
                            price = quote_currency.compute(float(label.Rate.Amount), currency_order)

                        if carrier_tracking_ref:
                            carrier_tracking_ref += " , "
                        carrier_tracking_ref += label.TrackingNumber
                        if stamps_transaction_id:
                            stamps_transaction_id += " , "
                        stamps_transaction_id += label.StampsTxID
                        if label.URL:
                            url = label.URL
                            label_cre = (requests.get(url).content)
                            logmessage = (_("Shipment created into Stamps <br/> <b>Tracking Number : </b>%s <br/> <b>Stamps transaction id : </b>%s") % (carrier_tracking_ref,stamps_transaction_id))
                            picking.message_post(body=logmessage, attachments=[('LabelStamps-%s.png' % (carrier_tracking_ref), label_cre)])
                        if label.ImageData:
                            label_cre =  label.ImageData.base64Binary
                            logmessage = (_("Shipment created into Stamps <br/> <b>Tracking Number : </b>%s <br/> <b>Stamps transaction id  : </b>%s") % (carrier_tracking_ref,stamps_transaction_id))
                            for label_binary_data in label_cre:
                                labels.append(('LabelStamps-%s.%s' % (label.TrackingNumber, picking.carrier_id.stamps_label_file_type), base64.b64decode(label_binary_data)))
                                # labels.append(('LabelStamps-%s.%s' % (label.TrackingNumber, picking.carrier_id.stamps_label_file_type), label_binary_data.decode('base64')))
                picking.message_post(body=logmessage, attachments=labels)
            else:
                try:
                    rate = service.get_rates(ret_val)[0]
                except Exception as e:
                    raise ValidationError(e)
                ret_val.Amount = rate.Amount
                ret_val.DeliverDays = rate.DeliverDays
                ret_val.DimWeighting = rate.DimWeighting
                ret_val.Zone = rate.Zone
                ret_val.RateCategory = rate.RateCategory
                ret_val.ToState = rate.ToState
                if picking.partner_id.apo_fpo_dpo:
                    products = [line.product_id.name for line in picking.move_lines if line.quantity_done >= line.product_uom_qty]
                    ret_val.DeclaredValue = rate.Amount
                    customs = service.create_customs()
                    customs.ContentType.value = picking.carrier_id.stamps_content_type
                    custom_line = service.create_customs_lines()
                    custom_line.Description = ",".join(products)
                    custom_line.Quantity = sum([line.quantity_done for line in picking.move_lines])
                    custom_line.Value = rate.Amount
                    custom_line.WeightLb = tot_weight
                    custom_line.CountryOfOrigin = picking.picking_type_id.warehouse_id.partner_id.country_id.code
                    customs.CustomsLines.CustomsLine.append(custom_line)
                    ret_val.PrintLayout = 'Normal4X6CN22Thermal'
                transaction_id = str(picking.name) + str(datetime.now().isoformat())
                label = service.get_label(from_address, to_address, ret_val, transaction_id=transaction_id, sample=sample, image_type=picking.carrier_id.stamps_label_file_type, memo=memo, customs=customs)
                if label:
                    currency_order = picking.sale_id.currency_id
                    if not currency_order:
                        currency_order = picking.company_id.currency_id

                    # USPS always returns prices in USD
                    if currency_order.name == "USD":
                        price = float(label.Rate.Amount)
                    else:
                        quote_currency = self.env['res.currency'].search([('name', '=', "USD")], limit=1)
                        price = quote_currency.compute(float(label.Rate.Amount), currency_order)

                    carrier_tracking_ref = label.TrackingNumber
                    labels = []
                    if label.URL:
                        url = label.URL
                        label_cre = (requests.get(url).content)

                        logmessage = (_("Shipment created into Stamps <br/> <b>Tracking Number : </b>%s <br/> <b>Stamps transaction id : </b>%s") % (carrier_tracking_ref,label.StampsTxID))
                        picking.message_post(body=logmessage, attachments=[('LabelStamps-%s.png' % (carrier_tracking_ref), label_cre)])
                    if label.ImageData:
                        label_cre =  label.ImageData.base64Binary
                        logmessage = (_("Shipment created into Stamps <br/> <b>Tracking Number : </b>%s <br/> <b>Stamps transaction id  : </b>%s") % (carrier_tracking_ref,label.StampsTxID))
                        for label_binary_data in label_cre:
                            labels.append(('LabelStamps-%s.%s' % (label.TrackingNumber, picking.carrier_id.stamps_label_file_type), base64.b64decode(label_binary_data)))
                            # labels.append(('LabelStamps-%s.%s' % (carrier_tracking_ref, picking.carrier_id.stamps_label_file_type), label_binary_data.decode('base64')))
                        picking.message_post(body=logmessage, attachments=labels)

            shipping_data = {'exact_price': price,
                             'tracking_number': carrier_tracking_ref}
            res = res + [shipping_data]
            return res

    def stamps_get_tracking_link(self, picking):
        tracking_ref = picking.carrier_tracking_ref.split(',')
        tracking_lnik = 'http://www.stamps.com/shipstatus/?confirmation=%s' % tracking_ref[0]
        return tracking_lnik

    def stamps_account_info(self):
        superself = self.sudo()
        if not self.prod_environment:
            prod_environment = 'testing'
        else:
            prod_environment = None
        config_proc = StampsConfiguration(integration_id=superself.stamps_integration_id,username=superself.stamps_username, password=superself.stamps_password, wsdl=prod_environment)
        service = StampsService(config_proc)
        account = service.get_account()
        if account.AccountInfo.PostageBalance:
            raise ValidationError(_("Current available Postage Balance :  %s") % (float(account.AccountInfo.PostageBalance.AvailablePostage)))

    def stamps_cancel_shipment(self, picking):
        superself = self.sudo()
        if self.prod_environment:
            prod_environment = None
            config_proc = StampsConfiguration(integration_id=superself.stamps_integration_id,username=superself.stamps_username, password=superself.stamps_password, wsdl=prod_environment)
            service = StampsService(config_proc)
            if len(picking.package_ids)>1:
                tracking_ref = picking.carrier_tracking_ref.split(',')
                for track in tracking_ref:
                    result = service.remove_label(track)
            else:
                result = service.remove_label(picking.carrier_tracking_ref)
            picking.message_post(body=_(u'Shipment N° %s has been cancelled' % picking.carrier_tracking_ref))
            picking.write({'carrier_tracking_ref': '',
                           'carrier_price': 0.0})
        else:
            picking.message_post(body=_(u'Shipment N° %s has been cancelled' % picking.carrier_tracking_ref))
            picking.write({'carrier_tracking_ref': '',
                           'carrier_price': 0.0})

    @api.multi
    def return_postage_wiz(self):
        if not self.prod_environment:
            prod_environment = 'testing'
        else:
            prod_environment = None
        ctx = dict(self.env.context or {})
        ctx.update({
            'integration_id':self.stamps_integration_id,
            'user_name':self.stamps_username,
            'password':self.stamps_password,
            'prod_env':prod_environment,
            'carrier_id':self.id,
        })
        vform = self.env.ref(
            'stamps_integration_drc.add_postage_wizard_form', False)
        return {
            'name': 'Purchase Postage',
            'views': [(vform.id, 'form')],
            'view_id': vform.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'postage.add',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }


class NewPostageAdd(models.TransientModel):
    _name = "postage.add"

    postage_amount = fields.Float(string="Postage Amount")

    @api.multi
    def add_postage(self):
        ctx = self.env.context
        if ctx.get('integration_id') and ctx.get('user_name') and ctx.get('password') and ctx.get('prod_env'):
            int_id = ctx.get('integration_id')
            u_name = ctx.get('user_name') 
            pwd = ctx.get('password') 
            p_env = ctx.get('prod_env')
            config_proc = StampsConfiguration(integration_id=int_id,username=u_name, password=pwd, wsdl=p_env)
            service = StampsService(config_proc)

            transaction_id = datetime.now().isoformat()
            result = service.add_postage(self.postage_amount, transaction_id=transaction_id)
            transaction_id = result.TransactionID
            status = service.create_purchase_status()
            
            carrier = self.env['delivery.carrier'].search([('id','=',int(ctx.get('carrier_id')))])
            carrier.stamps_transaction_id = result.TransactionID
            if result.PurchaseStatus in (status.Pending , status.Processing):
                raise ValidationError(_("Current Postage status is %s. \n Current transaction id is : %s") % (result.PurchaseStatus,result.TransactionID))
            if result.PurchaseStatus in (status.Success):
                raise ValidationError(_("Postage balance is updated successfully. \n Current transaction id is : %s") % (result.TransactionID))
            if result.PurchaseStatus in (status.Rejected):
                raise ValidationError(_("Current transaction is Rejected."))
        else:
            raise ValidationError(_("Please check the credentials"))