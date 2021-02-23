# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = 'sale.order'   

    purolator_shipping_date =  fields.Date(string='Shipping Date', default=fields.Date.today()) 
    purolator_total_weight =  fields.Float(string='Total Weight') 
    purolator_weight_unit = fields.Selection([('LB', 'LB'), ('KG', 'KG')], default='KG', string="Weight Unit") 
    purolator_service = fields.Char(string="Purolator Service")
    purolator_service_type = fields.Many2one(comodel_name="purolator.service", string="Select Service Type")
    purolator_get_service = fields.Boolean(string='Select Service Options')
    delivery_purolator = fields.Boolean(string='Is delivery purolator?', default=False)


    @api.onchange("purolator_service")
    def onchange_purolator_service(self):
        return {'domain': {'purolator_service_type': [('choise_id','=',self.id), ('active','=',True)]}}

    @api.onchange("purolator_service_type")
    def onchange_my_selection_id(self):
        self.delivery_price = self.purolator_service_type.total_price
        self.display_price = self.purolator_service_type.total_price

    @api.onchange("carrier_id")
    def onchange_carrier_id(self):
        if self.carrier_id:
            total_weight= 0
            self.delivery_purolator = False
            if 'purolator' in self.carrier_id.name.lower():
                self.delivery_purolator = True
                for line in self.order_line:
                    total_weight += line.product_id.weight if line.product_id.weight != False and line.is_delivery == False else 0
                    if self.purolator_weight_unit.lower() != line.product_id.weight_uom_name:
                        total_weight = total_weight*2.2
                self.purolator_total_weight = total_weight  

    @api.onchange('carrier_id')
    def _onchange_carrier_id_2(self):
        order = self.env['sale.order'].search([('name','=',self.name)])
        if order:
            res = {'domain':{'purolator_service_type':[('active','=',True),('id','=',order.id)]}}
        else:
            res = {'domain':{'purolator_service_type':[('active','=',True)]}}
        return res

    @api.onchange("purolator_weight_unit")
    def onchange_weight_unit(self):
        if self.carrier_id:
            total_weight= 0
            if 'purolator' in self.carrier_id.name.lower():
                for line in self.order_line:
                    total_weight += line.product_id.weight if line.product_id.weight != False and line.is_delivery == False else 0
                    if self.purolator_weight_unit.lower() != line.product_id.weight_uom_name:
                        total_weight = total_weight*2.2
                self.purolator_total_weight = total_weight                         

    @api.model
    def update_delivery_line(self,service_id):
        for order in self:
            new_service_rate = 0
            for line in order.order_line:
                if line._is_delivery() == True:
                    service_id = self.env['purolator.service'].sudo().search(['|',('active','=',True),('active','=',False),('id','=',int(service_id))])
                    new_service_rate = service_id.total_price
                    line.price_unit = new_service_rate
            return {'status':True, 'new_service_rate':new_service_rate}

class ProductProduct(models.Model):
    _inherit = 'product.product'   

    country_of_manufacture = fields.Many2one('res.country', string='Country of Manufacture')

class ProductTemplate(models.Model):
    _inherit = 'product.template'   

    country_of_manufacture = fields.Many2one('res.country', string='Country of Manufacture')
