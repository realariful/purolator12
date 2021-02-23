# -*- coding: utf-8 -*-

import logging
import time
from odoo import api, models, fields, _, tools
from odoo.exceptions import UserError
from odoo.tools import pdf
from .purolator_request import PurolatorRequest

_logger = logging.getLogger(__name__)

class ProviderPurolator(models.Model):
    # _inherit = 'choose.delivery.package'
    _inherit = 'sale.order'

    purolator_shipping_date =  fields.Date(string='Shipping Date', default=fields.Date.today()) 
    purolator_total_weight =  fields.Float(string='Total Weight') 
    purolator_weight_unit = fields.Selection([('LB', 'LB'), ('KG', 'KG')], default='KG', string="Weight Unit") 
    purolator_service = fields.Char(string="Purolator Service")
    purolator_service_type = fields.Many2one(comodel_name="purolator.service", string="Select Service Type")
    purolator_get_service = fields.Boolean(string='Select Service Options')
      
    @api.onchange("purolator_service")
    def onchange_purolator_service(self):
        return {'domain': {'purolator_service_type': [('choise_id','=',self.id), ('active','=',True)]}}

    @api.onchange("purolator_service_type")
    def onchange_my_selection_id(self):
        self.delivery_price = self.purolator_service_type.total_price
        self.display_price = self.purolator_service_type.total_price

    @api.onchange("carrier_id")
    def onchange_carrier_id(self):
        sers = self.env['purolator.service'].sudo().search([])
        for ser in sers:
            ser.sudo().write({'active':False})
           
class MySelectionModel(models.Model):
    _name = "purolator.service"
    _description = "Purolator Services"

    service_id = fields.Char(string="Service ID")
    shipment_date =  fields.Date(string='Shipment Date')  
    expected_delivery_date =  fields.Date(string='Expected Delivery Date')
    expected_transit_days =  fields.Integer(string='EstimatedTransitDays')
    surcharges = fields.Float(string="Surcharges")   
    taxes = fields.Float(string="Taxes") 
    options = fields.Float(string="Optional") 
    base_price = fields.Float(string="Base Price")  
    total_price = fields.Float(string="Display Price")   
    order_id = fields.Many2one('sale.order')
    choise_id = fields.Integer('choose.delivery.package')
    # choise_id = fields.Many2one('choose.delivery.package')
    active = fields.Boolean(string='Status', default=True)

    def name_get(self):
        res = []
        for record in self:
            if record.service_id:
                name = record.service_id + ', Shipping Cost: ' + str(record.total_price) + ', Expected Delivery Date: ' + str(record.expected_delivery_date)
                res.append((record.id,  name))    
        return res
