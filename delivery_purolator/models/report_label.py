# -*- coding: utf-8 -*-

from odoo import tools
from odoo import api, fields, models
from odoo.exceptions import Warning, ValidationError, UserError
from .purolator_request import PurolatorRequest



class StockPickingInherit(models.Model):    
    _inherit = 'stock.picking'

    @api.model
    def print_shipping_label(self, docids, data=None):
        attachment_id = self.env['ir.attachment'].search(['|',('name','like','LabelPurolator'),('name','like','CANADA'),('res_id','=',docids[0])])
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

    @api.model
    def generate_shipping_label(self, docids, data=None):
        print(self.carrier_tracking_ref)
        pick = self.env['stock.picking'].sudo().browse(docids[0])
        pins = pick.carrier_tracking_ref
        if pins:
            pick.carrier_id.purolator_get_labels(pick.carrier_tracking_ref, pick)
        
        
      
