# -*- coding: utf-8 -*-

import logging, requests
from odoo import models, exceptions, _


_logger = logging.getLogger(__name__)


class SyncBMProducts(models.TransientModel):
    _name = 'cenit.wireless.sync_bm_products'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def sync_bm_products(self):
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
        Product = self.env['product.product']

        try:
            # Get my listings. Return only the listings having the given publication state.
            url = '{bm_url}/ws/listings/?publication_state=2'.format(bm_url=bm_url)
            _logger.info("[GET] %s", '%s' % url)
            response = requests.get(url=url, headers=headers)
            if 200 <= response.status_code < 300:
                listings = response.json()
            else:
                raise exceptions.AccessError()

            updates = 0
            for listing in listings.get('results'):
                product = Product.search([('default_code', '=', listing.get('sku'))], limit=1)

                if product and product.virtual_available != int(listing.get('quantity')):
                    # Update specific Listing
                    url = '{bm_url}/ws/listings/{listing_id}'.format(bm_url=bm_url, listing_id=listing.get('listing_id'))
                    payload = {
                        "quantity": product.virtual_available,
                    }
                    _logger.info("[POST] %s ? %s ", '%s' % url, payload)
                    requests.post(url=url, headers=headers, json=payload)
                    updates += 1
            self.message_post(body=_('%s products were updated in BackMarket' % updates), subtype='mail.mt_comment', author_id=self.create_uid.partner_id.id)
        except Exception as e:
            _logger.error(e)
            raise exceptions.AccessError(
                _("Error trying to connect to Backmarket (%s), please check the settings integrations") % url)

