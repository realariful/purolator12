# -*- coding: utf-8 -*-
import logging
import time
from odoo import api, models, fields, _, tools
from odoo.exceptions import UserError
from odoo.tools import pdf
from .purolator_request import PurolatorRequest
from decimal import *
_logger = logging.getLogger(__name__)
import os

try:
    import requests
except ImportError:
    _logger.info("Unable to import requests, please install it with pip install requests")

class ProviderPurolator(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('purolator', "Purolator")])
    purolator_developer_key = fields.Char(string="Developer Key", groups="base.group_system")
    purolator_developer_password = fields.Char(string="Developer Password", groups="base.group_system")
    purolator_activation_key = fields.Char(string="Test Activation Key", groups="base.group_system")
    purolator_billing_account = fields.Char(string="Billing Account Number", groups="base.group_system")
    purolator_production_key = fields.Char(string="Production Key", groups="base.group_system")
    purolator_production_password = fields.Char(string="Production Password", groups="base.group_system")
    purolator_dropoff_type = fields.Selection([ ('DropOff', 'DROPOFF'),
                                                ('PreScheduled', 'PRESCHEDULED'),],
                                                    string="Purolator Drop Off type",
                                                    default='DropOff')
    purolator_default_packaging_id = fields.Many2one('product.packaging', string="Default Package Type")
    purolator_service_type = fields.Selection([ ('PurolatorExpress','Purolator Express'),
                                                ('PurolatorExpress10:30AM','Purolator Express 10:30AM'),
                                                ('PurolatorExpress12PM','Purolator Express 12PM'),
                                                ('PurolatorExpress9AM','Purolator Express 9AM'),
                                                ('PurolatorExpressBox','Purolator Express Box'),
                                                ('PurolatorExpressBox10:30AM','Purolator Express Box 10:30AM'),
                                                ('PurolatorExpressBox12PM','Purolator Express Box 12PM'),
                                                ('PurolatorExpressBox9AM','Purolator ExpressBox 9AM'),
                                                ('PurolatorExpressBoxEvening','Purolator Express Box Evening'),
                                                ('PurolatorExpressBoxInternational','Purolator Express Box International'),
                                                ('PurolatorExpressBoxU.S.','Purolator Express Box U.S.'),
                                                ('PurolatorExpressEnvelope','Purolator Express Envelope'),
                                                ('PurolatorExpressEnvelope10:30AM','Purolator Express Envelope 10:30AM'),
                                                ('PurolatorExpressEnvelope12PM','Purolator Express Envelope 12PM'),
                                                ('PurolatorExpressEnvelope9AM','Purolator Express Envelope 9AM'),
                                                ('PurolatorExpressEnvelopeEvening','Purolator Express Envelope Evening'),
                                                ('PurolatorExpressEnvelopeInternational','Purolator Express Envelope International'),
                                                ('PurolatorExpressEnvelopeU.S.','Purolator Express Envelope U.S.'),
                                                ('PurolatorExpressEvening','Purolator Express Evening'),
                                                ('PurolatorExpressInternational','Purolator Express International'),
                                                ('PurolatorExpressInternational10:30AM','Purolator Express International 10:30AM'),
                                                ('PurolatorExpressInternational12:00','Purolator Express International 12:00'),
                                                ('PurolatorExpressInternational10:30AM','Purolator Express International 10:30AM'),
                                                ('PurolatorExpressInternational9AM','Purolator Express International 9AM'),
                                                ('PurolatorExpressInternationalBox10:30AM','Purolator Express International Box 10:30AM'),
                                                ('PurolatorExpressInternationalBox12:00','Purolator Express International Box12:00'),
                                                ('PurolatorExpressInternationalBox9AM','Purolator Express International Box 9AM'),
                                                ('PurolatorExpressInternationalEnvelope10:30AM','Purolator Express International Envelope 10:30AM'),
                                                ('PurolatorExpressInternationalEnvelope12:00','Purolator Express International Envelope 12:00'),
                                                ('PurolatorExpressInternationalEnvelope9AM','Purolator Express International Envelope 9AM'),
                                                ('PurolatorExpressInternationalPack10:30AM','Purolator Express International Pack 10:30 AM'),
                                                ('PurolatorExpressInternationalPack12:00','Purolator Express International Pack 12:00'),
                                                ('PurolatorExpressInternationalPack9AM','Purolator Express International Pack 9AM'),
                                                ('PurolatorExpressPack','Purolator Express Pack'),
                                                ('PurolatorExpressPack10:30AM','Purolator ExpressPack 10:30AM'),
                                                ('PurolatorExpressPack12PM','Purolator Express Pack 12PM'),
                                                ('PurolatorExpressPack9AM','Purolator Express Pack 9AM'),
                                                ('PurolatorExpressPackEvening','Purolator Express Pack Evening'),
                                                ('PurolatorExpressPackInternational','Purolator Express Pack International'),
                                                ('PurolatorExpressPackU.S.','Purolator Express Pack U.S.'),
                                                ('PurolatorExpressU.S.','Purolator Express U.S.'),
                                                ('PurolatorExpressU.S.10:30AM','Purolator Express U.S. 10:30AM'),
                                                ('PurolatorExpressU.S.12:00','Purolator Express U.S. 12:00'),
                                                ('PurolatorExpressU.S.9AM','Purolator Express U.S. 9AM'),
                                                ('PurolatorExpressU.S.Box10:30AM','Purolator Express U.S. Box 10:30AM'),
                                                ('PurolatorExpressU.S.Box12:00','Purolator Express U.S. Box 12:00'),
                                                ('PurolatorExpressU.S.Box9AM','Purolator Express U.S. Box 9AM'),
                                                ('PurolatorExpressU.S.Envelope10:30AM','Purolator Express U.S. Envelope 10:30AM'),
                                                ('PurolatorExpressU.S.Envelope12:00','Purolator Express U.S. Envelope 12:00'),
                                                ('PurolatorExpressU.S.Envelope9AM','Purolator Express U.S. Envelope 9AM'),
                                                ('PurolatorExpressU.S.Pack10:30AM','Purolator Express U.S. Pack 10:30AM'),
                                                ('PurolatorExpressU.S.Pack12:00','PurolatorExpress U.S. Pack 12:00'),
                                                ('PurolatorExpressU.S.Pack9AM','PurolatorExpress U.S. Pack 9AM'),
                                                ('PurolatorGround','Purolator Ground'),
                                                ('PurolatorGround10:30AM','Purolator Ground 10:30AM'),
                                                ('PurolatorGround9AM','Purolator Ground 9AM'),
                                                ('PurolatorGroundDistribution','Purolator Ground Distribution'),
                                                ('PurolatorGroundEvening','Purolator Ground Evening'),
                                                ('PurolatorGroundRegional','Purolator Ground Regional'),
                                                ('PurolatorGroundU.S.','Purolator Ground U.S.'),
                                                ('PurolatorQuickShip','Purolator Quick Ship'),
                                                ('PurolatorQuickShipBox','Purolator Quick Ship Box'),
                                                ('PurolatorQuickShipEnvelope','Purolator Quick Ship Envelope'),
                                                ('PurolatorQuickShipPack','Purolator Quick Ship Pack'),        
                                                 ],'Purolator Service Type', default='PurolatorExpress')
    purolator_payment_type = fields.Selection([ ('Sender', 'Sender'), 
                                                ('Receiver', 'Receiver'),
                                                ('ThirdParty', 'ThirdParty'), 
                                                ('CreditCard', 'CreditCard')], 
                                                string="Purolator Payment Type", required=True, default="Sender")
    purolator_creditcard_type = fields.Selection([  ('Visa', 'Visa'), 
                                                    ('MasterCard', 'MasterCard'),
                                                    ('AmericanExpress', 'AmericanExpress'),], 
                                                    string="Credit Card Type", groups="base.group_system")
    purolator_creditcard_number = fields.Integer(string="Credit Card Number", groups="base.group_system")
    purolator_creditcard_name = fields.Char(string="Credit Card Name", groups="base.group_system")
    purolator_creditcard_expirymonth = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'),
                                                        ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), 
                                                        ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12'), ], 
                                                        string="Expiry Month", groups="base.group_system")
    purolator_creditcard_expiryyear = fields.Char(string="Expiry Year", groups="base.group_system")
    purolator_creditcard_cvv = fields.Char(string="CVV", groups="base.group_system")
    purolator_creditcard_billingpostalcode = fields.Char(string="Billing Postal Code", groups="base.group_system")
    purolator_weight_unit = fields.Selection([('LB', 'LB'),
                                              ('KG', 'KG')],
                                            default='KG')
    purolator_printer_type = fields.Selection([('Regular', 'Regular (8" x 11")'),
                                                ('Thermal', 'Thermal (6" x 4")'),],
                                             default='Thermal', string="Purolator Printer Type")
    purolator_customer_type = fields.Char(string="Customer Type", groups="base.group_system")
    purolator_customer_number = fields.Char(string="Customer Number", groups="base.group_system")
    purolator_promo_code = fields.Char(string="Promo Code", groups="base.group_system")
    purolator_label_image_format = fields.Selection([('PDF', 'PDF'),],
                                             default='PDF', string="Purolator Label File Type")
    purolator_default_weight = fields.Float("Default Weight",default=1.00, readonly=True, groups="base.group_system")
    purolator_product_uom = fields.Many2one("uom.uom","Odoo Product UoM", groups="base.group_system")
    purolator_api_uom = fields.Char("API UoM",default="KG", readonly=True, groups="base.group_system")
    purolator_void_shipment = fields.Boolean("Void Shipment", default=True, groups="base.group_system")
    purolator_shipment_type = fields.Selection([('domestic', 'Domestic'),
                                                ('us', 'US'),
                                                ('int', 'International')],
                                                string='Shipment Type', default='domestic')    
    purolator_from_onlabel = fields.Boolean("From on Label Indicator", default=False, groups="base.group_system")
    purolator_from_onlabel_info = fields.Selection([('same', 'Same as Company Address'),
                                                    ('diff', 'Different')],
                                                    string='From On Label Selection', default='same')
    purolator_label_info = fields.Many2one('res.partner', string='From On Label Partner')
    purolator_notify_sender = fields.Boolean("Email Notification for Sender", default=False, groups="base.group_system")
    purolator_notify_receiver = fields.Boolean("Email Notification for Receiver", default=False, groups="base.group_system")
    purolator_buyer = fields.Selection([('same', 'Same as Receiver'),
                                        ('diff', 'Different')],
                                        string='Buyer Information', default='same')
    purolator_buyer_info = fields.Many2one('res.partner', string='Buyer Contact')
    purolator_preferred_customs = fields.Char(string='Preferred Customs Broker')
    purolator_duty_party = fields.Selection([('sender', 'Sender'),
                                            ('receiver', 'Receiver'),
                                            ('buyer', 'Buyer')],
                                            string='Duty Party', default='sender')   
    purolator_duty_currency = fields.Selection([('cad', 'CAD'),
                                            ('us', 'USD'),      ],                                     
                                            string ='Duty Currency', default='cad')       
    purolator_business_relation = fields.Selection([('related', 'Related'),
                                                    ('notrelated', 'Not Related'),],                                     
                                            string ='Business Relation', default='notrelated')  
    purolator_nafta_document = fields.Boolean("NAFTA Document Indicator", default=False, groups="base.group_system")
    purolator_fda_document = fields.Boolean("FDA Document Indicator", default=False, groups="base.group_system")
    purolator_fcc_document = fields.Boolean("FCC Document Indicator", default=False, groups="base.group_system")
    purolator_sender_is_producer = fields.Boolean("Sender Is Producer Indicator", default=False, groups="base.group_system")
    purolator_textile_indicator = fields.Boolean("Textile Indicator", default=False, groups="base.group_system")
    purolator_textile_manufacturer= fields.Char("Textile Manufacturer", default=False, groups="base.group_system")

    @api.onchange('purolator_service_type')
    def _onchange_service_type(self):
        self.purolator_shipment_type = 'domestic'
        if 'U.S.' in self.purolator_service_type:
            self.purolator_shipment_type = 'us'
        if 'International' in self.purolator_service_type:
            self.purolator_shipment_type = 'int'

    def _compute_can_generate_return(self):
        super(ProviderPurolator, self)._compute_can_generate_return()
        for carrier in self:
            if not carrier.can_generate_return:
                if carrier.delivery_type == 'purolator':
                    carrier.can_generate_return = True

    def purolator_service_options(self, order, ship_date):
        services = []
        try:
            superself = self.sudo()        
            KEY = superself.purolator_production_key if superself.prod_environment == True else superself.purolator_developer_key
            PASS = superself.purolator_production_password if superself.prod_environment == True else superself.purolator_developer_password
            val = PurolatorRequest(self.log_xml, request_type="services", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
            val.web_authentication_detail(KEY, PASS)         
            val_req = val.address_validate(order.company_id.partner_id, order.partner_id)  
            if not val_req.get('errors_message'):
                srm = PurolatorRequest(self.log_xml, request_type="services", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
                srm.web_authentication_detail(KEY, PASS)        
                request = srm.service_options(order.warehouse_id.partner_id, order.partner_shipping_id, self.purolator_billing_account,ship_date )
                warnings = request.get('warnings_message')
                if warnings:
                    _logger.info(warnings)
                if not request.get('errors_message'):
                    services = request.get('services')
                else:
                    if request.get('errors_message') == (401, 'Unauthorized'):
                        request['errors_message'] = "Wrong Purolator Credentials. Please provide correct credentials in Purolator Confirguration."
                    return {'success': False,
                            'services':services,
                            'error_message': _('Error:\n%s') % str(request['errors_message']),
                            'warning_message': False}
            else:
                return {'success': False,
                            'services': services,
                            'error_message': _('Error:\n%s') % str(val_req['errors_message']),
                            'warning_message': False}          
            return {'success': True,
                    'services': services,
                    'error_message': False,
                    'warning_message': _('Warning:\n%s') % warnings if warnings else False}
        except Exception as e:
            return {'success': False,
                'services': services,
                'error_message': _(e.args),
                'warning_message': False}


    def purolator_rate_shipment(self, order):
        print("purolator_rate_shipment")   
        order.write({'state':'draft'})
        purolator_service_request = self.purolator_service_type
        purolator_service_type = []
        if order.purolator_service_type:
            if order.purolator_service_type.service_id:
                if order.purolator_service_type.service_id != self.purolator_service_type:
                    purolator_service_request = order.purolator_service_type.service_id
                    # print(purolator_service_request)
        else:
            print("No service available")
        max_weight = self._purolator_convert_weight(self.purolator_default_packaging_id.max_weight, self.purolator_weight_unit)
        price = 0.0
        # if order.carrier_id:
        #     choice = order.carrier_id#self.env['choose.delivery.package'].search([('order_id','=',order.id),('carrier_id','=',order.carrier_id.id)],order='id desc',limit=1)
        # else:
        #     choice = self.env['choose.delivery.package'].search([('order_id','=',order.id),('carrier_id','=',self.id)],order='id desc',limit=1)
        choice = self or order.carrier_id
        if len(choice) == 0:
            pass
        if len(choice) == 1 and order.purolator_total_weight:
            est_weight_value = order.purolator_total_weight
            weight_value = self._purolator_convert_weight(est_weight_value, self.purolator_weight_unit)
        else:
            est_weight_value = sum([(line.product_id.weight * line.product_uom_qty) for line in order.order_line if not line.display_type]) or 0.0
            weight_value = self._purolator_convert_weight(est_weight_value, self.purolator_weight_unit)

        if 'Pack' and 'Envelope' not in purolator_service_request:
            if weight_value == 0.0:
                if self.purolator_weight_unit == 'KG':
                    weight_value =  0.45
                else:
                    weight_value =  1.00
        order_currency = order.currency_id
        superself = self.sudo()
        # Authentication stuff
        
        KEY = superself.purolator_production_key if self.prod_environment == True else superself.purolator_developer_key
        PASS = superself.purolator_production_password if superself.prod_environment == True else superself.purolator_developer_password
        val = PurolatorRequest(self.log_xml, request_type="services", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
        val.web_authentication_detail(KEY, PASS)     
        val_req = val.address_validate(order.company_id.partner_id, order.partner_id)  

        if not val_req.get('errors_message'):
            srm = PurolatorRequest(self.log_xml, request_type="rating", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
            srm.web_authentication_detail(KEY, PASS)        
            srm.set_shipper(order.company_id.partner_id, order.warehouse_id.partner_id)
            srm.set_recipient(order.partner_shipping_id)
            srm.shipment_request(purolator_service_request,weight_value,self.purolator_weight_unit,self.purolator_dropoff_type)
            if self.purolator_shipment_type != 'domestic':
                srm.set_international_info(order.order_line,self.purolator_nafta_document,self.purolator_fda_document,self.purolator_fcc_document,self.purolator_sender_is_producer
                        ,self.purolator_textile_indicator,self.purolator_textile_manufacturer, order.partner_shipping_id, self.purolator_buyer, self.purolator_buyer_info) 
            if self.purolator_notify_sender == True:
                email1 = order.company_id.partner_id.email 
            else:
                email1 = ''

            if self.purolator_notify_receiver == True:
                email2 = order.partner_shipping_id.email 
            else:
                email2 = ''
            srm.set_email_notify(email1, email2)
            srm.set_tracking_reference(order)
            RegisteredAccountNumber = self.purolator_billing_account
            srm.shipping_charges_payment(self.purolator_payment_type, self.purolator_billing_account, RegisteredAccountNumber)

            pkg = self.purolator_default_packaging_id
            if max_weight and weight_value > max_weight:
                total_package = int(weight_value / max_weight)
                last_package_weight = weight_value % max_weight

                for sequence in range(1, total_package + 1):
                    srm.add_package(
                        max_weight,
                        package_code=pkg.shipper_package_code,
                        package_height=pkg.height,
                        package_width=pkg.width,
                        package_length=pkg.length,
                        sequence_number=sequence,
                        mode='rating',
                    )
                if last_package_weight:
                    total_package = total_package + 1
                    srm.add_package(
                        last_package_weight,
                        package_code=pkg.shipper_package_code,
                        package_height=pkg.height,
                        package_width=pkg.width,
                        package_length=pkg.length,
                        sequence_number=total_package,
                        mode='rating',
                    )
                srm.set_master_package(weight_value, total_package)
            else:
                srm.add_package(
                    weight_value,
                    package_code=pkg.shipper_package_code,
                    package_height=pkg.height,
                    package_width=pkg.width,
                    package_length=pkg.length,
                    mode='rating',
                )
                srm.set_master_package(weight_value, 1)
            request = srm.rate(purolator_service_request)
            warnings = request.get('warnings_message')
            if request.get('warnings_message') == 'Error:\nThe server was unable to process the request due to an internal error.  For more information about the error, either turn on IncludeExceptionDetailInFaults (either from ServiceBehaviorAttribute or from the <serviceDebug> configuration behavior) on the server in order to send the exception information back to the client, or turn on tracing as per the Microsoft .NET Framework SDK documentation and inspect the server trace logs.':
                warnings = 'Error:\nThe server was unable to process the request due to an internal error.'
            if warnings:
                _logger.info(warnings)
            ShipmentEstimate = []
            if not request.get('errors_message'):
                
                ShipmentEstimate = request.get('ShipmentEstimate')
                price = request['price']['TotalPrice']
                # This works
                choice = self#.env['choose.delivery.package'].search([('order_id','=',order.id),('carrier_id','=',self.id)],order='id desc',limit=1)
                # choice.purolator_service_type = self.purolator_service_type
                sers = self.env['purolator.service'].sudo().search([])
                for ser in sers:
                    ser.write({'active':False})
                for rating in ShipmentEstimate:
                    surcharges_total = Decimal('0.0')
                    for item in rating['Surcharges']['Surcharge']:
                        surcharges_total += item['Amount']
                    taxes_total = Decimal('0.0')
                    for item in rating['Taxes']['Tax']:
                        taxes_total += item['Amount']
                    options_total = Decimal('0.0')
                    for item in rating['OptionPrices']['OptionPrice']:
                        options_total += item['Amount']
                    rate = self.env['purolator.service'].sudo().create(
                        {
                            'service_id' : rating.ServiceID ,
                            'shipment_date' :   rating.ShipmentDate,
                            'expected_delivery_date' :   rating.ExpectedDeliveryDate,
                            'expected_transit_days' :   rating.EstimatedTransitDays,
                            'base_price' :   rating.BasePrice,
                            'surcharges' :   float(surcharges_total),
                            'taxes' :   float(taxes_total),
                            'options' :   float(options_total),
                            'total_price' :   rating.TotalPrice,
                            'order_id' :   order.id,
                            'choise_id': choice.id,
                            'active': True
                        })   

                    if rate:
                        rating['service_id'] = str(rate.id)
                    if rating.ServiceID == self.purolator_service_type:
                        # print("rating.ServiceID == self.purolator_service_type")
                        # choice.purolator_service_type = rate.id
                        choice.purolator_service_type = rating.ServiceID
                
                purolator_service_type = self.env['purolator.service'].sudo().search([('order_id','=',order.id),('active','=',True)])
                # order.purolator_service_type = purolator_service_type.ids
                # for service in purolator_service_type:
                #     order.purolator_service_type.append(service.id)
            else:
                if request.get('errors_message') == (401, 'Unauthorized'):
                    request['errors_message'] = "Wrong Purolator Credentials. Please provide correct credentials in Purolator Confirguration."
                res = {'success': False,
                        'price': 0.0,
                        'ShipmentEstimate' : [],
                        'error_message': _('Error:\n%s') % str(request['errors_message']),
                        'purolator_service_type': [],
                        'warning_message': False}
        

            service_id = False
            if len(purolator_service_type) > 0 :
                for ser in purolator_service_type:
                    if price == ser.total_price:
                        service_id = ser.id
                        order.write({'purolator_service_type':ser.id})
            res = {'success': True,
                    'price': price,
                    'ShipmentEstimate' : ShipmentEstimate,
                    'error_message': False,
                    'purolator_service_type': service_id,
                    'warning_message': _('Warning:\n%s') % warnings if warnings else False}

            # Response for Free Shipment
            if res['success'] and self.free_over and order._compute_amount_total_without_delivery() >= self.amount:
                print("FREE SHIPMENT")
                res['free_delivery'] = True
            else:
                res['free_delivery'] = False
                print("NOT FREE SHIPMENT")
        else:
            res =  {'success': False,
                        'price': 0.0,
                        'ShipmentEstimate' : [],
                        'error_message': _('Error:\n%s') % str(val_req['errors_message']),
                        'purolator_service_type': [],
                        'warning_message': False}  

        return res


    def purolator_send_shipping(self, pickings): 
        print("purolator_send_shipping")       
        res = []
        for picking in pickings: 
            purolator_service_type = self.purolator_service_type
            if picking.sale_id.purolator_service_type:
                if picking.sale_id.purolator_service_type.service_id:
                    if picking.sale_id.purolator_service_type.service_id != self.purolator_service_type:
                        purolator_service_type = picking.sale_id.purolator_service_type.service_id
            # else:
            #     print(purolator_service_type)

            srm = PurolatorRequest(self.log_xml, request_type="shipping", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
            superself = self.sudo()
            KEY = superself.purolator_production_key if self.prod_environment == True else superself.purolator_developer_key
            PASS = superself.purolator_production_password if self.prod_environment == True else superself.purolator_developer_password
             
            srm.web_authentication_detail(KEY, PASS)
            package_type = picking.package_ids and picking.package_ids[0].packaging_id.shipper_package_code or self.purolator_default_packaging_id.shipper_package_code
            weight_value = '1'   
            if 'Pack' and 'Envelope' not in purolator_service_type:
                if weight_value == 0.0:
                    if self.purolator_weight_unit == 'KG':
                        weight_value =  0.45
                    else:
                        weight_value =  1.00

            order = picking.sale_id
            company = order.company_id or picking.company_id or self.env.company
            order_currency = picking.sale_id.currency_id or picking.company_id.currency_id
            net_weight = self._purolator_convert_weight(picking.shipping_weight, self.purolator_weight_unit)
            srm.set_shipper(order.company_id.partner_id, order.warehouse_id.partner_id)
            srm.set_recipient(order.partner_shipping_id)
            srm.shipment_request(purolator_service_type, weight_value,self.purolator_weight_unit,self.purolator_dropoff_type)
            if self.purolator_shipment_type != 'domestic':
                srm.set_international_info(order.order_line,self.purolator_nafta_document,self.purolator_fda_document,self.purolator_fcc_document,self.purolator_sender_is_producer
                        ,self.purolator_textile_indicator,self.purolator_textile_manufacturer, order.partner_shipping_id, self.purolator_buyer, self.purolator_buyer_info) 
            if self.purolator_notify_sender == True:
                email1 = order.company_id.partner_id.email 
            else:
                email1 = ''
            if self.purolator_notify_receiver == True:
                email2 = order.partner_shipping_id.email 
            else:
                email2 = ''
            srm.set_email_notify(email1, email2)
            srm.set_tracking_reference(order)
            srm.shipping_charges_payment(self.purolator_payment_type, self.purolator_billing_account, self.purolator_billing_account)
            package_count = len(picking.package_ids) or 1
            po_number = order.display_name or False
            dept_number = False
            ################
            # Multipackage #
            ################
            if package_count > 1:
                master_tracking_id = False
                package_labels = []
                carrier_tracking_ref = ""
                for sequence, package in enumerate(picking.package_ids, start=1):
                    package_weight = self._purolator_convert_weight(package.shipping_weight, self.purolator_weight_unit)
                    packaging = package.packaging_id
                    srm._add_package(
                        package_weight,
                        package_code=packaging.shipper_package_code,
                        package_height=packaging.height,
                        package_width=packaging.width,
                        package_length=packaging.length,
                        sequence_number=sequence,
                        po_number=po_number,
                        dept_number=dept_number,
                        reference=picking.display_name,
                    )
                    srm.set_master_package(net_weight, package_count, master_tracking_id=master_tracking_id)
                    request = srm.process_shipment(self.purolator_printer_type)
                    package_name = package.name or sequence

                    warnings = request.get('warnings_message')
                    if warnings:
                        _logger.info(warnings)

                    if sequence == 1:
                        if not request.get('errors_message'):
                            master_tracking_id = request['master_tracking_id']
                            lrm = PurolatorRequest(self.log_xml, request_type="label", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
                            lrm.web_authentication_detail(KEY,PASS)
                            get_label_url = lrm.get_label_url(master_tracking_id,self.purolator_label_image_format)
                            _logger.info(get_label_url)
                            if get_label_url['error'] == None:
                              for url in get_label_url['url']:
                                    bytepdf = self.get_pdf_byte(url)
                                    package_labels.append((package_name, bytepdf))
                            carrier_tracking_ref = request['tracking_number']
                        else:
                            raise UserError(request['errors_message'])
                    # Intermediary packages
                    elif sequence > 1 and sequence < package_count:
                        if not request.get('errors_message'):
                            lrm = PurolatorRequest(self.log_xml, request_type="label", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
                            lrm.web_authentication_detail(KEY,PASS)
                            get_label_url = lrm.get_label_url(master_tracking_id,self.purolator_label_image_format)
 
                            if get_label_url['error'] == None:
                                purolator_labels=[]
                                for url in get_label_url['url']:
                                    bytepdf = self.get_pdf_byte(url)
                                    package_labels.append((package_name, bytepdf))
                            carrier_tracking_ref = carrier_tracking_ref + "," + request['tracking_number']
                        else:
                            raise UserError(request['errors_message'])
                    # Last package
                    elif sequence == package_count:
                        if not request.get('errors_message'):
                            if picking.sale_id:
                                carrier_price = order.amount_delivery
                            else:
                                carrier_price = 0


                            lrm = PurolatorRequest(self.log_xml, request_type="label", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
                            lrm.web_authentication_detail(KEY,PASS)
                            get_label_url = lrm.get_label_url(master_tracking_id,self.purolator_label_image_format)
                            if get_label_url['error'] == None:
                                purolator_labels=[]
                                for url in get_label_url['url']:
                                    _logger.info(get_label_url)
                                    bytepdf = self.get_pdf_byte(url)
                                    package_labels.append((package_name, bytepdf))

                            carrier_tracking_ref = carrier_tracking_ref + "," + request['tracking_number']
                            logmessage = _("Shipment created into purolator<br/>" +str(purolator_service_type) +
                                           "<b>Tracking Numbers:</b> %s<br/>"
                                           "<b>Packages:</b> %s") % (carrier_tracking_ref, ','.join([pl[0] for pl in package_labels]))
                            if self.purolator_label_image_format != 'PDF':
                                attachments = [('Labelpurolator-%s.%s' % (pl[0], self.purolator_label_image_format), pl[1]) for pl in package_labels]
                            if self.purolator_label_image_format == 'PDF':
                                attachments = [('Labelpurolator.pdf', pdf.merge_pdf([pl[1] for pl in package_labels]))]
                            picking.message_post(body=logmessage, attachments=attachments)
                            shipping_data = {'exact_price': carrier_price, 'tracking_number': carrier_tracking_ref}
                            res = res + [shipping_data]
                        else:
                            raise UserError(request['errors_message'])

            ###############
            # One package #
            ###############
            elif package_count == 1:
                packaging = picking.package_ids[:1].packaging_id or picking.carrier_id.purolator_default_packaging_id
                srm._add_package(
                    net_weight,
                    package_code=packaging.shipper_package_code,
                    package_height=packaging.height,
                    package_width=packaging.width,
                    package_length=packaging.length,
                    po_number=po_number,
                    dept_number=dept_number,
                    reference=picking.display_name,
                )
                srm.set_master_package(net_weight, 1)
                # Ask the shipping to purolator
                request = srm.process_shipment(self.purolator_printer_type)
                warnings = request.get('warnings_message')
                if warnings:
                    _logger.info(warnings)
                if not request.get('errors_message'):
                    carrier_tracking_ref = request['tracking_number']#Array of PINS
                    print(carrier_tracking_ref)
                    carrier_price = 0.0
                    for line in order.order_line:
                        if line.is_delivery == True:
                            carrier_price = line.price_subtotal
                    _logger.info(carrier_price)
                    if request['master_tracking_id']:
                        # self.prod_environment = True
                        # carrier_tracking_ref = '332780309891'
                        lrm = PurolatorRequest(self.log_xml, request_type="label", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
                        # KEY = 'f1affe37c6a14c9d8e65206b2dd42adf'
                        # PASS = 'm4/ebT&S'
                        # print(KEY)
                        # print(PASS)
                        lrm.web_authentication_detail(KEY,PASS)
                        get_label_url = lrm.get_label_url(carrier_tracking_ref,self.purolator_label_image_format)
                        if get_label_url['error'] == None:
                            purolator_labels = []
                            _logger.info(get_label_url)
                            # url_new  = 'https://eshiponline.purolator.com/ShipOnline/shipment/getLabel.ashx?i=j5I2Evo%2b3sJOXAVRHbnCngCDjjaq%2bQA94d7oUP%2bpvbRclwWvxUyY7bOzUOIOmg0eJ26WB4Txwv6rY0YC1aYjLZgVIPkCWa61JqhNKjE9VGKE4g2g%2bp96H1aBBAkXfEFmeeaG3qATe%2fCwfBp84Vy5d7Svbtodi3pnsNkGx08pj2k%3d'
                            # get_label_url['url'] = [url_new]
                            for url in get_label_url['url']:
                                bytepdf = self.get_pdf_byte(url)
                                PDF_NAME = 'LabelPurolator-%s.%s' % (carrier_tracking_ref, self.purolator_label_image_format)                        
                                purolator_labels.append((PDF_NAME,bytepdf))
                                order_currency = picking.sale_id.currency_id or self.company_id.currency_id
                                logmessage = _("Shipment sent to carrier %s for shipping with <br/> <b>Tracking Number : </b> %s<br/>") % (picking.carrier_id.name, carrier_tracking_ref)
                                picking.message_post(body=logmessage, attachments=purolator_labels)
                            shipping_data = {'exact_price': carrier_price, 'tracking_number': carrier_tracking_ref}
                            res = res + [shipping_data]
                else:
                    raise UserError(request['errors_message'])

            ##############
            # No package #
            ##############
            else:
                raise UserError(_('No packages for this picking'))
            return res

    def purolator_get_tracking_link(self, pickings):
        return 'https://www.purolator.com/en/shipping/tracker?pins=' + '%s' % pickings.carrier_tracking_ref

    def purolator_cancel_shipment(self, picking):
        picking.message_post(body=_(u"You can't cancel Purolator shipping without pickup date."))
        picking.write({'carrier_tracking_ref': '', 'carrier_price': 0.0})

    def _purolator_convert_weight(self, weight, unit='KG'):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        if unit == 'KG':
            return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'), round=False)
        elif unit == 'LB':
            return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_lb'), round=False)
        else:
            raise ValueError

    def get_pdf_byte(self,url):
        try:
            myfile = requests.get(url)
            bytepdf = bytearray(myfile.content)
            return bytepdf
            # import base64
            # myfile = requests.get(url)
            # base64_encoded_data = base64.b64encode(myfile.content)
            # base64_message = base64_encoded_data.decode('utf-8')
            # return base64_message
        except Exception as e:
            raise UserError(str(e.args))

    def purolator_get_labels(self, carrier_tracking_ref, picking):
        try:
            import pdb;pdb.set_trace()
            superself = self.sudo()        
            KEY = superself.purolator_production_key if superself.prod_environment == True else superself.purolator_developer_key
            PASS = superself.purolator_production_password if superself.prod_environment == True else superself.purolator_developer_password
            # self.prod_environment = True
            # carrier_tracking_ref = '332780309891'
            print(self.log_xml,self.prod_environment,self.purolator_activation_key)
            lrm = PurolatorRequest(self.log_xml, request_type="label", prod_environment=self.prod_environment,purolator_activation_key=self.purolator_activation_key)
            # KEY = 'f1affe37c6a14c9d8e65206b2dd42adf'
            # PASS = 'm4/ebT&S'
            # print(KEY, PASS)
            lrm.web_authentication_detail(KEY,PASS)
            get_label_url = lrm.get_label_url(carrier_tracking_ref,self.purolator_label_image_format)
            
            _logger.info(get_label_url)
            if get_label_url['error'] == None:
                purolator_labels = []
                _logger.info(get_label_url)
                for url in get_label_url['url']:
                    bytepdf = self.get_pdf_byte(url)
                    PDF_NAME = 'LabelPurolator-%s.%s' % (carrier_tracking_ref, self.purolator_label_image_format)                        
                    purolator_labels.append((PDF_NAME,bytepdf))
                    order_currency = picking.sale_id.currency_id or self.company_id.currency_id
                    logmessage = _("Downloaded Shipping Labels")
                    picking.message_post(body=logmessage, attachments=purolator_labels)
        except Exception as e:
            print(e.args)