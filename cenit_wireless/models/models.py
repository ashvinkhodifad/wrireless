# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CenitSaleOrder(models.Model):
    _inherit = "sale.order"

    bm_id = fields.Char(string=_('Backmarket id'))


    #metodo de prueba
    @api.depends('partner_id')
    @api.model
    def customer_verify(self):
        import uuid
        return {'postdata_arr': [
            {
                "id": str(uuid.uuid4()).replace('-',''),
                "ExternalCode": "0002",
                "Requester": "Odoo",
                "AccountName": "Extensa-Test-Vincent2",
                "AccountType": "Levenrancier",
                "Address": "streetname 4c",
                "ZipCode": "8570",
                "City": "Vichte",
                "Country": "BE",
                "ContactName": "Niusvel",
                "PhoneNumber": "+53395088",
                "Email": "nisuvel@gmail.com",
                "VATNumber": "0",
                "BankAccount": "",
                "Valuta": "EUR"
            },
            {
                "id": str(uuid.uuid4()).replace('-', ''),
                "ExternalCode": "0002",
                "Requester": "Odoo",
                "AccountName": "Extensa-Test-Vincent2",
                "AccountType": "Levenrancier",
                "Address": "streetname 4c",
                "ZipCode": "8570",
                "City": "Vichte",
                "Country": "BE",
                "ContactName": "Niusvel",
                "PhoneNumber": "+53395088",
                "Email": "nisuvel@gmail.com",
                "VATNumber": "0",
                "BankAccount": "",
                "Valuta": "EUR"
            },
            {
                "id": str(uuid.uuid4()).replace('-', ''),
                "ExternalCode": "0002",
                "Requester": "Odoo",
                "AccountName": "Extensa-Test-Vincent2",
                "AccountType": "Levenrancier",
                "Address": "streetname 4c",
                "ZipCode": "8570",
                "City": "Vichte",
                "Country": "BE",
                "ContactName": "Niusvel",
                "PhoneNumber": "+53395088",
                "Email": "nisuvel@gmail.com",
                "VATNumber": "0",
                "BankAccount": "",
                "Valuta": "EUR"
            },
            {
                "id": str(uuid.uuid4()).replace('-', ''),
                "ExternalCode": "0002",
                "Requester": "Odoo",
                "AccountName": "Extensa-Test-Vincent2",
                "AccountType": "Levenrancier",
                "Address": "streetname 4c",
                "ZipCode": "8570",
                "City": "Vichte",
                "Country": "BE",
                "ContactName": "Niusvel",
                "PhoneNumber": "+53395088",
                "Email": "nisuvel@gmail.com",
                "VATNumber": "0",
                "BankAccount": "",
                "Valuta": "EUR"
            }
        ]}

    @api.model
    def check_order_aviablity(self,order_ids):
        return {'aviability':order_ids}

