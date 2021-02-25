# -*- coding: utf-8 -*-

from odoo import tools
from odoo import api, fields, models
from odoo.exceptions import Warning, ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class StockPickingInherit(models.Model):    
    _inherit = 'stock.picking'

    @api.model
    def print_shipping_label(self, docids, data=None):
        attachment_id = self.env['ir.attachment'].search([('name','like','LabelPurolator'),('res_id','=',docids[0])],order='id desc',limit=1)
        if attachment_id:
            download_url = '/web/content/' + str(attachment_id.id) + '?download=True'
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')       
            return {       
                "type": "ir.actions.act_url",      
                "url": str(base_url)  +  str(download_url),      
                "target": "new",    
                }
        else:
            raise UserError("No Shipping Label founf for current shipment")


    def get_shipping_label(self, docids, data=None):
        picking = self.env['stock.picking'].browse(docids)  if len(self) == 0 else self
        if picking:
            picking.carrier_id.get_labels(picking)
    
    def get_label_url(self, docids, data=None):
        picking = self.env['stock.picking'].browse(docids)  if len(self) == 0 else self
        print(picking.carrier_tracking_ref)
        if picking:
            get_label_urls = picking.carrier_id.get_label_urls(picking)
            _logger.info(get_label_urls)
            if get_label_urls['url']:
                return {       
                    "type": "ir.actions.act_url",      
                    "url": get_label_urls['url'],      
                    "target": "new",    
                    }

    def _sync_labels(self):
        _logger.info("SYnc Labels")
        pickings = self.env['stock.picking'].sudo().search([('carrier_id.delivery_type','=','purolator'),('state','=', 'done')])
        _logger.info(pickings)
        for pick in pickings:
            attachments = self.env['ir.attachment'].sudo().search([('res_model','=','stock.picking'),('res_id','=',pick.id)])
            if not attachments and pick.carrier_tracking_ref:
                _logger.info('No attachments found ')
                _logger.info(pick.carrier_tracking_ref)
                pick.carrier_id.get_labels(pick)
        
      
