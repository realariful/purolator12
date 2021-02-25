# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery
from werkzeug.utils import redirect
from decimal import *

show_services = ['PurolatorExpress','PurolatorExpressU.S.','PurolatorExpressInternational','PurolatorGround']      
class WebsiteSaleDeliveryInherit(WebsiteSaleDelivery):

    @http.route(['/shop/update_carrier'], type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def update_eshop_carrier(self, **post):
        order = request.website.sale_get_order()
        carrier_id = int(post['carrier_id'])
        if order:
            order._check_carrier_quotation(force_carrier_id=carrier_id)
        service_id = ''
        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id))   
        purolator_service_rates = []
        minimum_rate = 0
        if carrier.delivery_type == 'purolator':
            purolator_service_type = request.env['purolator.service'].sudo().search([('choise_id','=',carrier_id),('active','=',True)])
            select_service = False
            if purolator_service_type:
                minimum_rate = purolator_service_type[0].total_price
                for record in purolator_service_type:
                    if record.total_price  < minimum_rate:
                        minimum_rate = record.total_price
                        select_service = record.id
                    name = record.service_id + ',Shipping Cost: \n ' + str(record.total_price) + ',\n Expected Delivery Date: ' + str(record.expected_delivery_date)
                    purolator_service_rates.append({
                        'value':record.id,
                        'name':name,
                        'total_price': '%0.2f' %record.total_price,
                        'service_id' : record.service_id ,
                        'shipment_date' :   record.shipment_date,
                        'expected_delivery_date' :   record.expected_delivery_date,
                        'expected_transit_days' :   record.expected_transit_days,
                        'base_price' :   '%0.2f' %record.base_price,
                        'surcharges' : '%0.2f' % record.surcharges,
                        'taxes' :   '%0.2f' %record.taxes,
                        'options' :   record.options,
                        'total_price' :   '%0.2f' %record.total_price,
                        'order_id' :   record.order_id.id,
                        'choise_id': carrier_id,
                    })
            order.update_delivery_line(select_service)
        post['purolator_service_rates'] = purolator_service_rates
        delivery_line = order.order_line.filtered('is_delivery')
        for service in request.env['purolator.service'].search([('order_id','=',order.id)]):
            if service.total_price == delivery_line.price_subtotal:   
                service_id = service.id
        post['service_id'] = service_id
        return self._update_website_sale_delivery_return(order, **post)

    @http.route(['/shop/carrier_rate_shipment'], type='json', auth='public', methods=['POST'], website=True)
    def cart_carrier_rate_shipment(self, carrier_id, **kw):
        order = request.website.sale_get_order(force_create=True)
        assert int(carrier_id) in order._get_delivery_methods().ids, "unallowed carrier"
        Monetary = request.env['ir.qweb.field.monetary']
        res = {'carrier_id': carrier_id}
        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id))    
        rate = carrier.rate_shipment(order)    
        purolator_service_rates = []
        service_id = ''
        minimum_rate = 0
        if carrier.delivery_type == 'purolator':
            purolator_service_type = request.env['purolator.service'].sudo().search([('order_id','=',order.id)])
            if purolator_service_type:
                minimum_rate = purolator_service_type[0].total_price
                for record in purolator_service_type:
                    name = record.service_id + ', Shipping Cost: ' + str(record.total_price) + ', Expected Delivery Date: ' + str(record.expected_delivery_date)
                    purolator_service_rates.append({
                        'value':record.id,
                        'name':name
                    })
                    if record.service_id in show_services:
                        if record.total_price  < minimum_rate:
                            minimum_rate = record.total_price
                            service_id = record.id   
                        order.update_delivery_line(service_id)
                         
        ShipmentEstimate = rate.get('ShipmentEstimate')
        if ShipmentEstimate != None:
            ShipmentEstimate = self.process_rate_purolator(ShipmentEstimate,order)    
        if rate.get('success'):
            res['status'] = True
            res['new_amount_delivery'] = Monetary.value_to_html(minimum_rate, {'display_currency': order.currency_id})
            res['is_free_delivery'] = not bool(minimum_rate)
            res['error_message'] = rate['warning_message']
            res['service_id'] = str(service_id)
            res['ShipmentEstimate'] = rate.get('ShipmentEstimate')
            res['purolator_service_type'] = purolator_service_rates
            res['free_delivery'] = rate.get('free_delivery')
        else:
            res['status'] = False
            res['new_amount_delivery'] = Monetary.value_to_html(0.0, {'display_currency': order.currency_id})
            res['error_message'] = rate['error_message']
            res['ShipmentEstimate'] = []
            res['purolator_service_type'] = purolator_service_rates
            res['service_id'] = str(service_id)
        return res

    def _update_website_sale_delivery_return(self, order, **post):
        Monetary = request.env['ir.qweb.field.monetary']
        carrier_id = int(post['carrier_id'])
        currency = order.currency_id
        carrier = request.env['delivery.carrier'].sudo().search([('id','=',carrier_id)])
        free_delivery = False
        if carrier and carrier.delivery_type == 'purolator':
            if post.get('purolator_service_rates') and carrier.free_over and order._compute_amount_total_without_delivery() >= carrier.amount:
                print("FREE SHIPMENT")
                order.amount_delivery = 0.0
                order._remove_delivery_line()
                free_delivery = True
        if order:
            return {
                'status': order.delivery_rating_success,
                'error_message': order.delivery_message,
                'carrier_id': carrier_id,
                'is_free_delivery': not bool(order.amount_delivery),
                'new_amount_delivery': self._format_amount(order.amount_delivery, currency),
                'new_amount_untaxed': self._format_amount(order.amount_untaxed, currency),
                'new_amount_tax': self._format_amount(order.amount_tax, currency),
                'new_amount_total': self._format_amount(order.amount_total, currency),
                'purolator_service_rates': post['purolator_service_rates'],
                'service_id': post['service_id'],
                'free_delivery':free_delivery,
            }
        return {}

    @http.route(['/shop/update_carrier_service'], type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def get_total_price(self, **post):
        order = request.website.sale_get_order()
        Monetary = request.env['ir.qweb.field.monetary']
        currency = order.currency_id
        update_delivery_line = order.update_delivery_line(post['service_id'])
        if post and update_delivery_line['status'] == True:
            data= {
                'status':True,
                'new_amount_delivery': self._format_amount(order.amount_delivery, currency),
                'new_amount_untaxed': self._format_amount(order.amount_untaxed, currency),
                'new_amount_tax': self._format_amount(order.amount_tax, currency),
                'new_amount_total': self._format_amount(order.amount_total, currency),
            }
        else:
             data= {
                'status':False,
                'new_amount_delivery': self._format_amount(order.amount_delivery, currency),
                'new_amount_untaxed': self._format_amount(order.amount_untaxed, currency),
                'new_amount_tax': self._format_amount(order.amount_tax, currency),
                'new_amount_total': self._format_amount(order.amount_total, currency),
            }      
        return data

    def process_rate_purolator(self, datas, order):
        Monetary = request.env['ir.qweb.field.monetary']
        if len(datas) > 0:
            for data in datas:
                surcharges_total = Decimal('0.0')
                for item in data['Surcharges']['Surcharge']:
                    surcharges_total += item['Amount']
                taxes_total = Decimal('0.0')
                for item in data['Taxes']['Tax']:
                    taxes_total += item['Amount']
                options_total = Decimal('0.0')
                for item in data['OptionPrices']['OptionPrice']:
                    options_total += item['Amount']
                data['surcharges_total'] =  Monetary.value_to_html(float(surcharges_total), {'display_currency': order.currency_id})
                data['taxes_total'] = Monetary.value_to_html(float(taxes_total), {'display_currency': order.currency_id}) 
                data['options_total'] = Monetary.value_to_html(float(options_total), {'display_currency': order.currency_id})
                data['BasePrice'] = Monetary.value_to_html(float(data['BasePrice']), {'display_currency': order.currency_id})
                data['TotalPrice'] = Monetary.value_to_html(float(data['TotalPrice']), {'display_currency': order.currency_id})
        return datas