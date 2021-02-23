# -*- coding: utf-8 -*-
import binascii
import logging
import os
import re
from odoo.exceptions import UserError

from datetime import datetime, date
from zeep import Client, Plugin, Settings
from zeep.exceptions import Fault
from zeep.wsse.username import UsernameToken
from requests import Session
from requests.auth import HTTPBasicAuth
from zeep.transports import Transport


_logger = logging.getLogger(__name__)
STATECODE_REQUIRED_COUNTRIES = ['US', 'CA', 'PR ', 'IN']

class LogPlugin(Plugin):
    """ Small plugin for zeep that catches out/ingoing XML requests and logs them"""
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger

    def egress(self, envelope, http_headers, operation, binding_options):
        self.debug_logger(envelope, 'fedex_request')
        return envelope, http_headers

    def ingress(self, envelope, http_headers, operation):
        self.debug_logger(envelope, 'fedex_response')
        return envelope, http_headers

    def marshalled(self, context):
        context.envelope = context.envelope.prune()

class PurolatorRequest():
    """ Low-level object intended to interface Odoo recordsets with Purolator, through appropriate SOAP requests """

    def __init__(self, debug_logger, request_type="shipping", prod_environment=False, purolator_activation_key=None):
        self.debug_logger = debug_logger
        self.hasCommodities = False
        self.hasOnePackage = False
        self.prod_environment = prod_environment
        if prod_environment:
            self.base_url = 'https://webservices.purolator.com/EWS/V2'
        else:
            self.base_url = 'https://devwebservices.purolator.com/EWS/V2'

        if request_type == "shipping":
            self.base_url= self.base_url +'/Shipping/ShippingService.wsdl'
            if not prod_environment:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../api/PurolatorEshipWS_Estimate_wsdl/Development/EstimatingService.wsdl')
            else:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../api/PurolatorEshipWS_Estimate_wsdl/Production/EstimatingService.wsdl')
            self.start_shipping_transaction(wsdl_path,purolator_activation_key)
            
        elif request_type == "rating":
            self.base_url= self.base_url +'/Estimating/EstimatingService.wsdl'
            if not prod_environment:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),  '../api/PurolatorEshipWS_Shipment_wsdl/Development/ShippingService.wsdl')
            else:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../api/PurolatorEshipWS_Shipment_wsdl/Production/ShippingService.wsdl')
            self.start_rating_transaction(wsdl_path,purolator_activation_key)

        elif request_type == "label":
            self.base_url= self.base_url.split("/V2")[0] +'/V1/ShippingDocuments/ShippingDocumentsService.wsdl'
            if not prod_environment:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),  '../api/PurolatorEshipWS_GetDocuments_wsdl/Development/ShippingDocumentsService.wsdl')
            else:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../api/PurolatorEshipWS_GetDocuments_wsdl/Production/ShippingDocumentsService.wsdl')        
            self.start_label_transaction(wsdl_path,purolator_activation_key)

        elif request_type == "services":
            self.base_url= self.base_url +'/ServiceAvailability/ServiceAvailabilityService.wsdl'
            if not prod_environment:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),  '../api/PurolatorEshipWS_ServiceAvailability_wsdl/Development/ServiceAvailabilityService.wsdl')
            else:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../api/PurolatorEshipWS_ServiceAvailability_wsdl/Production/ServiceAvailabilityService.wsdl')        
            self.set_soapheaders(wsdl_path,purolator_activation_key)

        elif request_type == "tracking":
            self.base_url= self.base_url.split("/V2")[0] +'/V1/Tracking/TrackingService.wsdl'
            if not prod_environment:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),  '../api/PurolatorEshipWS_Tracking_wsdl/Development/TrackingService.wsdl')
            else:
                wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../api/PurolatorEshipWS_Tracking_wsdl/Production/TrackingService.wsdl')        
            self.set_soapheaders(wsdl_path,purolator_activation_key)


    # Authentification stuff
    def web_authentication_detail(self, key, password):
        session = Session()
        session.auth = HTTPBasicAuth(key, password)
        self.client = Client(self.base_url,
            transport=Transport(session=session))

    # Common stuff
    def address_validate(self, warehouse_partner, recipient_partner):
        formatted_response = {'address_validate': False}
        try:
            ArrayOfShortAddress = self.factory.ArrayOfShortAddress()
            SenderAddress = self.factory.ShortAddress()
            SenderAddress.City = warehouse_partner.city if warehouse_partner.city != False else ''
            if warehouse_partner.country_id.code in STATECODE_REQUIRED_COUNTRIES:
                SenderAddress.Province = warehouse_partner.state_id.code if warehouse_partner.state_id != False else ''
            else:
                SenderAddress.Province  = ''
            SenderAddress.Country = warehouse_partner.country_id.code if warehouse_partner.country_id != False else ''
            SenderAddress.PostalCode = warehouse_partner.zip.replace(" ","") if warehouse_partner.zip != False else ''
            ArrayOfShortAddress.ShortAddress.append(SenderAddress)
            ReceiverAddress = self.factory.ShortAddress()
            ReceiverAddress.City = recipient_partner.city if recipient_partner.city != False else ''
            if recipient_partner.country_id.code in STATECODE_REQUIRED_COUNTRIES:
                ReceiverAddress.Province = recipient_partner.state_id.code if recipient_partner.state_id != False else ''
            else:
                ReceiverAddress.Province  = ''
            ReceiverAddress.Country = recipient_partner.country_id.code if recipient_partner.country_id != False else ''
            ReceiverAddress.PostalCode = recipient_partner.zip.replace(" ","") if recipient_partner.zip != False else ''
            ArrayOfShortAddress.ShortAddress.append(ReceiverAddress)  
            
            self.response  = self.client.service.ValidateCityPostalCodeZip(ArrayOfShortAddress,
                                                _soapheaders={'RequestContext': self.RequestContext})
            # print(self.response)
            if self.response.body.ResponseInformation.Errors == None:
                formatted_response['address_validate'] = True
            else:
                errors_message = '\n'.join([("%s: %s" % (n.Code, n.Description)) for n in self.response.body.ResponseInformation.Errors.Error if self.response.body.ResponseInformation.Errors != None])
                formatted_response['errors_message'] = errors_message
        except Fault as fault:
            formatted_response['errors_message'] = fault
        except IOError:
            formatted_response['errors_message'] = "Purolator Server Not Found"
        except Exception as e:
            formatted_response['errors_message'] = e.args[0]
        return formatted_response


    def set_shipper(self, company_partner, warehouse_partner):
        self.Shipment = self.factory.Shipment()
        SenderInformation = self.factory.SenderInformation()
        SndAddress = self.factory.Address()

        if warehouse_partner.is_company:
            SndAddress.Name = warehouse_partner.name
            SndAddress.Company = warehouse_partner.name
        else:
            SndAddress.Name  = warehouse_partner.name
            SndAddress.Company = warehouse_partner.parent_id.name or False
        if warehouse_partner.street == False and warehouse_partner.street2 == False:
            SndAddress.StreetName = None
        elif warehouse_partner.street2 == False:
            SndAddress.StreetName = warehouse_partner.street
        elif warehouse_partner.street == False:
            SndAddress.StreetName = warehouse_partner.street2
        else:
            SndAddress.StreetName = warehouse_partner.street + warehouse_partner.street2

        SndAddress.City = warehouse_partner.city or ''
        if warehouse_partner.country_id.code in STATECODE_REQUIRED_COUNTRIES:
            SndAddress.Province = warehouse_partner.state_id.code or ''
        else:
            SndAddress.Province = ''
        SndAddress.Country = warehouse_partner.country_id.code or ''
        SndAddress.PostalCode = warehouse_partner.zip.replace(" ","") if warehouse_partner.zip != False else ''
        SndPhoneNumber = self.factory.PhoneNumber()
        snd_phone_or = warehouse_partner.phone.replace('-','').replace('(','').replace(')','') if warehouse_partner.phone != False else warehouse_partner.phone
        snd_phone_sp = snd_phone_or.replace(' ','') if snd_phone_or != False else False 

        if snd_phone_sp != False:
            # snd_phone_cn_code = snd_phone_sp[0] if len(snd_phone_sp) > 1  else "+"+ str(warehouse_partner.country_id.phone_code)
            # if len(snd_phone_sp) > 1:
            #     snd_arr = snd_phone_sp[1]
            # else:
            #     snd_arr = snd_phone_sp[0]
            # snd_phone_ar_code = snd_arr[-10:-7] if len(snd_arr) > 3 else False
            # snd_phone = snd_arr[-7:] if len(snd_arr) > 3 else False
            snd_phone_cn_code = snd_phone_sp[:-10] if len(snd_phone_sp) > 1  else "+"+ str(recipient_partner.country_id.phone_code)
            snd_phone_ar_code = snd_phone_sp[-10:-7] if len(snd_phone_sp) > 3 else False
            snd_phone = snd_phone_sp[-7:] if len(snd_phone_sp) > 3 else False
        else:
            snd_phone_cn_code = "+"+ str(warehouse_partner.country_id.phone_code) if len(warehouse_partner.country_id) > 0 else ''
            snd_phone_ar_code = ''
            snd_phone = ''

        # import pdb;pdb.set_trace()
        SndPhoneNumber.CountryCode = snd_phone_cn_code
        SndPhoneNumber.AreaCode = snd_phone_ar_code
        SndPhoneNumber.Phone = snd_phone
        SndAddress.PhoneNumber = SndPhoneNumber
        SenderInformation.Address = SndAddress
        self.Shipment.SenderInformation= SenderInformation
            
            
    def set_recipient(self, recipient_partner):
        ReceiverInformation = self.factory.ReceiverInformation()
        RcvAddress = self.factory.Address()
        if recipient_partner.is_company:
            RcvAddress.Name = recipient_partner.name
            RcvAddress.Company = recipient_partner.name
        else:
            RcvAddress.Name = recipient_partner.name
            RcvAddress.Company = recipient_partner.parent_id.name or ''
        if recipient_partner.street == False and recipient_partner.street2 == False:
            RcvAddress.StreetName = None
        elif recipient_partner.street2 == False:
            RcvAddress.StreetName = recipient_partner.street
        elif recipient_partner.street == False:
            RcvAddress.StreetName = recipient_partner.street2
        else:
            RcvAddress.StreetName = recipient_partner.street + recipient_partner.street2
        RcvAddress.City = recipient_partner.city or ''
        if recipient_partner.country_id.code in STATECODE_REQUIRED_COUNTRIES:
            RcvAddress.Province = recipient_partner.state_id.code or ''
        else:
            RcvAddress.Province  = ''
        RcvAddress.Country = recipient_partner.country_id.code or ''
        RcvAddress.PostalCode = recipient_partner.zip.replace(" ","") if recipient_partner.zip != False else ''
        RcvPhoneNumber = self.factory.PhoneNumber()
        rcv_phone_or = recipient_partner.phone.replace('-','').replace('(','').replace(')','') if recipient_partner.phone != False else recipient_partner.phone
        # print(recipient_partner.phone, rcv_phone_or)
        rcv_phone_sp = rcv_phone_or.replace(' ','') if rcv_phone_or != False else False  
        # print(rcv_phone_sp)
        if rcv_phone_sp != False:
            # rcv_phone_cn_code = rcv_phone_sp[0] if len(rcv_phone_sp) > 1  else "+"+ str(recipient_partner.country_id.phone_code)
            # if len(rcv_phone_sp) > 1:
            #     rcv_arr = rcv_phone_sp[1]
            # else:
            #     rcv_arr = rcv_phone_sp[0]
            # print('rcv_arr ====> ', rcv_arr)
            # rcv_phone_ar_code = rcv_arr[-10:-7] if len(rcv_arr) > 3 else False
            # rcv_phone = rcv_arr[-7:] if len(rcv_arr) > 3 else False
            rcv_phone_cn_code = rcv_phone_sp[:-10] if len(rcv_phone_sp) > 1  else "+"+ str(recipient_partner.country_id.phone_code)
            rcv_phone_ar_code = rcv_phone_sp[-10:-7] if len(rcv_phone_sp) > 3 else False
            rcv_phone = rcv_phone_sp[-7:] if len(rcv_phone_sp) > 3 else False
        else:
            rcv_phone_cn_code = "+"+ str(recipient_partner.country_id.phone_code) if len(recipient_partner.country_id) > 0 else ''
            rcv_phone_ar_code = ''
            rcv_phone = ''
        # print(rcv_phone_cn_code, '/ ', rcv_phone_ar_code, '/ ', rcv_phone)
        RcvPhoneNumber.CountryCode = rcv_phone_cn_code
        RcvPhoneNumber.AreaCode = rcv_phone_ar_code
        RcvPhoneNumber.Phone = rcv_phone
        RcvAddress.PhoneNumber = RcvPhoneNumber
        ReceiverInformation.Address = RcvAddress
        self.Shipment.ReceiverInformation = ReceiverInformation

    #FromOnLabelInformation
    def set_labelinfo(self, label_indicator, purolator_from_onlabel_info, partner_id):
        if label_indicator == True:
            self.Shipment.FromOnLabelIndicator = True
            self.FromOnLabelInformation = self.factory.FromOnLabelInformation()
            if purolator_from_onlabel_info == 'same':
                self.FromOnLabelInformation = self.Shipment.SenderInformation
            else:
                LabelAddress = self.factory.Address()
                if partner_id.is_company:
                    LabelAddress.Name = partner_id.name
                    LabelAddress.Company = partner_id.name
                else:
                    LabelAddress.Name  = partner_id.name
                    LabelAddress.Company = partner_id.parent_id.name or False
                if partner_id.street == False and partner_id.street2 == False:
                    LabelAddress.StreetName = None
                elif partner_id.street2 == False:
                    LabelAddress.StreetName = partner_id.street
                elif partner_id.street == False:
                    LabelAddress.StreetName = partner_id.street2
                else:
                    LabelAddress.StreetName = partner_id.street + partner_id.street2
                LabelAddress.City = partner_id.city or ''
                if partner_id.country_id.code in STATECODE_REQUIRED_COUNTRIES:
                    LabelAddress.Province = partner_id.state_id.code or ''
                else:
                    LabelAddress.Province = ''
                LabelAddress.Country = partner_id.country_id.code or ''
                LabelAddress.PostalCode = partner_id.zip.replace(" ","") if partner_id.zip != False else ''
                LabelPhoneNumber = self.factory.PhoneNumber()
                snd_phone_or = partner_id.phone.replace('-','').replace('(','').replace(')','') if partner_id.phone != False else partner_id.phone
                snd_phone_sp = snd_phone_or.replace(' ','') if snd_phone_or != False else False  
                if snd_phone_sp != False:
                    # snd_phone_cn_code = snd_phone_sp[0] if len(snd_phone_sp) > 1  else "+"+ str(partner_id.country_id.phone_code)
                    # if len(snd_phone_sp) > 1:
                    #     snd_arr = snd_phone_sp[1]
                    # else:
                    #     snd_arr = snd_phone_sp[0]
                    # snd_phone_ar_code = snd_arr[-10:-7] if len(snd_arr) > 3 else False
                    # snd_phone = snd_arr[-7:] if len(snd_arr) > 3 else False
                    snd_phone_cn_code = snd_phone_sp[:-10] if len(snd_phone_sp) > 1  else "+"+ str(recipient_partner.country_id.phone_code)
                    snd_phone_ar_code = snd_phone_sp[-10:-7] if len(snd_phone_sp) > 3 else False
                    snd_phone = snd_phone_sp[-7:] if len(snd_phone_sp) > 3 else False
                else:
                    snd_phone_cn_code = "+"+ str(partner_id.country_id.phone_code) if len(partner_id.country_id) > 0 else ''
                    snd_phone_ar_code = ''
                    snd_phone = ''
                LabelPhoneNumber.CountryCode = snd_phone_cn_code
                LabelPhoneNumber.AreaCode = snd_phone_ar_code
                LabelPhoneNumber.Phone = snd_phone
                self.FromOnLabelInformation.Address = LabelAddress
                LabelAddress.PhoneNumber = LabelPhoneNumber
                self.Shipment.FromOnLabelInformation= self.FromOnLabelInformation

    #Tracking Reference
    def set_tracking_reference(self, sale_order):        
        TrackingReferenceInformation = self.factory.TrackingReferenceInformation()
        TrackingReferenceInformation.Reference1 = sale_order.name
        TrackingReferenceInformation.Reference2 = ''
        TrackingReferenceInformation.Reference3 = ''
        self.Shipment.TrackingReferenceInformation = TrackingReferenceInformation

    #Packaing Information
    def set_master_package(self, total_weight, package_count, master_tracking_id=False):
        self.Shipment.PackageInformation.TotalWeight.Value = total_weight
        self.Shipment.PackageInformation.TotalPieces = package_count

    def add_package(self, weight_value, package_code=False, package_height=0, package_width=0, package_length=0, sequence_number=False, mode='shipping'):
        return self._add_package(weight_value=weight_value, package_code=package_code, package_height=package_height, package_width=package_width,
                                 package_length=package_length, sequence_number=sequence_number, mode=mode, po_number=False, dept_number=False)
    def _add_package(self, weight_value, package_code=False, package_height=0, package_width=0, package_length=0, sequence_number=False, mode='shipping', po_number=False, dept_number=False, reference=False):
        package = self.factory.Piece()
        if self.Shipment.PackageInformation.TotalWeight.WeightUnit.upper() == 'KG' and weight_value < 0.45:
            weight_value = 0.45
        if self.Shipment.PackageInformation.TotalWeight.WeightUnit.upper() == 'LB' and weight_value < 1:
            weight_value = 1.00
        package_weight = self.factory.Weight()
        package_weight.Value = weight_value
        package_weight.WeightUnit = self.Shipment.PackageInformation.TotalWeight.WeightUnit
        package.Weight = package_weight
        pkg_height = self.factory.Dimension()
        pkg_height.Value = package_height
        pkg_height.DimensionUnit = "in" if self.Shipment.PackageInformation.TotalWeight.WeightUnit == 'lb' else 'cm'
        package.Height = pkg_height
        pkg_width = self.factory.Dimension()
        pkg_width.Value = package_width
        pkg_width.DimensionUnit = "in" if self.Shipment.PackageInformation.TotalWeight.WeightUnit == 'lb' else 'cm'
        package.Width = pkg_width 
        pkg_length = self.factory.Dimension()
        pkg_length.Value = package_length
        pkg_length.DimensionUnit = "in" if self.Shipment.PackageInformation.TotalWeight.WeightUnit == 'lb' else 'cm'
        package.Length = pkg_length        
        if mode == 'rating':
            self.Shipment.PackageInformation.PiecesInformation.Piece.append(package)
        else:
            self.Shipment.PackageInformation.PiecesInformation.Piece.append(package) 
        self.Shipment.PackageInformation.PiecesInformation.DangerousGoodsDeclarationDocumentIndicator = False

    # Rating stuff
    def start_rating_transaction(self, wsdl_path,purolator_activation_key):
        settings = Settings(strict=False)
        self.client = Client('file:///%s' % wsdl_path.lstrip('/'), plugins=[LogPlugin(self.debug_logger)], settings=settings)
        self.factory = self.client.type_factory('ns1')
        RequestContext = {
                'Version': '2.0',
                'Language': 'en',
                'GroupID': 'SpawnCycles',
                'RequestReference': 'SpawnCycles Rating',                
            }
        if not self.prod_environment:
            RequestContext['UserToken'] = purolator_activation_key
        self.RequestContext = RequestContext

    def service_options(self, warehouse_partner, recipient_partner, BillingAccountNumber, purolator_shipping_date):
        formatted_response = {'price': {},'services':[]}
        try:
            self.ShipmentDate = purolator_shipping_date
            ArrayOfShortAddress = self.factory.ArrayOfShortAddress()
            SenderAddress = self.factory.ShortAddress()
            SenderAddress.City = warehouse_partner.city if warehouse_partner.city != False else ''
            if warehouse_partner.country_id.code in STATECODE_REQUIRED_COUNTRIES:
                SenderAddress.Province = warehouse_partner.state_id.code if warehouse_partner.state_id != False else ''
            else:
                SenderAddress.Province  = ''
            SenderAddress.Country = warehouse_partner.country_id.code if warehouse_partner.country_id != False else ''
            SenderAddress.PostalCode = warehouse_partner.zip.replace(" ","") if warehouse_partner.zip != False else ''
            ReceiverAddress = self.factory.ShortAddress()
            ReceiverAddress.City = recipient_partner.city if recipient_partner.city != False else ''
            if recipient_partner.country_id.code in STATECODE_REQUIRED_COUNTRIES:
                ReceiverAddress.Province = recipient_partner.state_id.code if recipient_partner.state_id != False else ''
            else:
                ReceiverAddress.Province  = ''
            ReceiverAddress.Country = recipient_partner.country_id.code if recipient_partner.country_id != False else ''
            ReceiverAddress.PostalCode = recipient_partner.zip if recipient_partner.zip != False else ''
            self.response = self.client.service.GetServicesOptions(BillingAccountNumber,SenderAddress,ReceiverAddress,self.ShipmentDate,
                _soapheaders={'RequestContext': self.RequestContext})
            if self.response.body.ResponseInformation.Errors == None:
                if len(self.response.body.Services.Service) == 0:
                    raise Exception("No services found")
                ServiceOptions = self.response.body.Services.Service
                if len(ServiceOptions) > 1:
                    for service in ServiceOptions:
                        formatted_response['services'].append((str(service.ID),str(service.Description)))
            else:
                errors_message = '\n'.join([("%s: %s" % (n.Code, n.Description)) for n in self.response.body.ResponseInformation.Errors.Error if self.response.body.ResponseInformation.Errors != None])
                formatted_response['errors_message'] = errors_message
        except Fault as fault:
            formatted_response['errors_message'] = fault
        except IOError:
            formatted_response['errors_message'] = "Purolator Server Not Found"
        except Exception as e:
            formatted_response['errors_message'] = e.args[0]
        return formatted_response

    def rate(self, service_type):
        formatted_response = {'price': {}, 'ShipmentEstimate':[]}
        try:
            self.ShowAlternativeServicesIndicator = True
            from pprint import pprint 
            # pprint(self.Shipment)
            # pprint(self.ShowAlternativeServicesIndicator)
            self.response = self.client.service.GetFullEstimate(self.Shipment,self.ShowAlternativeServicesIndicator,
                _soapheaders={'RequestContext': self.RequestContext})
            # print(self.response)

            if self.response.body.ResponseInformation.Errors == None:
                if len(self.response.body.ShipmentEstimates.ShipmentEstimate) == 0:
                    raise Exception("No rating found")
                ShipmentEstimate = self.response.body.ShipmentEstimates.ShipmentEstimate
                if len(ShipmentEstimate) > 1:
                    for rating in ShipmentEstimate:                        
                        if rating.ServiceID == service_type:
                            formatted_response['price']['TotalPrice'] = float(rating.TotalPrice)
                if len(ShipmentEstimate) == 1:
                    formatted_response['price']['TotalPrice'] = float(ShipmentEstimate[0].TotalPrice)            
                formatted_response['ShipmentEstimate'] = ShipmentEstimate  

            else:
                errors_message = '\n'.join([("%s: %s" % (n.Code, n.Description)) for n in self.response.body.ResponseInformation.Errors.Error if self.response.body.ResponseInformation.Errors != None])
                formatted_response['errors_message'] = errors_message
        except Fault as fault:
            formatted_response['errors_message'] = fault
        except IOError:
            formatted_response['errors_message'] = "Purolator Server Not Found"
        except Exception as e:
            formatted_response['errors_message'] = e.args[0]
        return formatted_response

    def start_shipping_transaction(self, wsdl_path,purolator_activation_key=None):
        settings = Settings(strict=False)
        self.client = Client('file:///%s' % wsdl_path.lstrip('/'), plugins=[LogPlugin(self.debug_logger)], settings=settings)
        self.factory = self.client.type_factory('ns1')
        RequestContext = {
                'Version': '2.0',
                'Language': 'en',
                'GroupID': 'Syncoria Client',
                'RequestReference': 'Syncoria Client Rating',                
            }
        if not self.prod_environment:
            RequestContext['UserToken'] = purolator_activation_key
        self.RequestContext = RequestContext    

    #Shipping Stuff
    def process_shipment(self,purolator_printer_type):
        formatted_response = {'tracking_number': 0.0,
                              'price': {},
                              'master_tracking_id': None,
                              'date': None}

        try:
            self.PrinterType = purolator_printer_type#'Thermal' or 'Regular'
            response2 = self.client.service.ValidateShipment(self.Shipment, _soapheaders={'RequestContext':self.RequestContext})
            if response2.body.ResponseInformation.Errors == None:
                self.response = self.client.service.CreateShipment(self.Shipment,self.PrinterType, _soapheaders={'RequestContext':self.RequestContext})
                if self.response.body.ShipmentPIN == None:
                    raise Exception("No Shipment Created")                 
                else:
                    if self.response.body.ResponseInformation.Errors == None:
                        if 'ShipmentPIN' in self.response.body:
                            formatted_response['master_tracking_id'] = self.response.body.ShipmentPIN.Value
                            formatted_response['tracking_number'] = self.response.body.ShipmentPIN.Value#self.response.body.PiecePINs.PIN
                    else:
                        errors_message='Shipment Creation Error:'
                        errors_message = '\n'.join([("%s: %s" % (n.Code, n.Description)) for n in self.response.body.ResponseInformation.Errors.Error if response2.body.ResponseInformation.Errors != None])
                        formatted_response['errors_message'] = errors_message
            else:
                errors_message='Shipment Validation Error:'
                errors_message = '\n'.join([("%s: %s" % (n.Code, n.Description)) for n in response2.body.ResponseInformation.Errors.Error if response2.body.ResponseInformation.Errors != None])
                formatted_response['errors_message'] = errors_message

        except Fault as fault:
            formatted_response['errors_message'] = fault
        except IOError:
            formatted_response['errors_message'] = "Purolator Server Not Found"
        except Exception as e:
            formatted_response['errors_message'] = e.args[0]
        return formatted_response

    def get_document(self, ManifestDate):
        self.ShipmentManifestDocumentCriteria = self.factory.ShipmentManifestDocumentCriteria()
        self.ShipmentManifestDocumentCriteria.ManifestDate = ManifestDate#'2020-05-17'
        
        doc_res = self.client.service.GetShipmentManifestDocument({'ShipmentManifestDocumentCriteria': self.ShipmentManifestDocumentCriteria}, 
        _soapheaders={'RequestContext': self.RequestContext})
        
        if doc_res.body.ResponseInformation.Errors == None:
            return doc_res.body.ManifestBatches.ManifestBatch[0].ManifestBatchDetails.ManifestBatchDetail[0].URL
        else:
            return False

    def shipping_charges_payment(self, PaymentType, BillingAccountNumber, RegisteredAccountNumber):
        PaymentInformation = self.factory.PaymentInformation()
        PaymentInformation.PaymentType = PaymentType
        PaymentInformation.RegisteredAccountNumber = RegisteredAccountNumber
        PaymentInformation.BillingAccountNumber = BillingAccountNumber
        self.Shipment.PaymentInformation = PaymentInformation

    def shipment_request(self, ServiceID,weight_value, purolator_weight_unit,PickupType):    
        PackageInformation = self.factory.PackageInformation()
        PackageInformation.ServiceID = ServiceID
        PackageInformation.Description = ServiceID#'UAT-TC005'
        TotalWeight = self.factory.TotalWeight()
        TotalWeight.Value = weight_value
        TotalWeight.WeightUnit = purolator_weight_unit.lower()
        self.Shipment.PackageInformation = PackageInformation
        self.Shipment.PackageInformation.TotalWeight =  TotalWeight
        PickupInformation =  self.factory.PickupInformation()
        PickupInformation.PickupType = PickupType
        self.Shipment.PickupInformation = PickupInformation
        self.Shipment.PackageInformation.PiecesInformation = self.factory.ArrayOfPiece()
     
    #InternationalInformation
    def set_international_info(self, so_lines,NAFTA,FDA,FCC,SIPI,Textile,TextileMan, recipient_partner, buyer, buyer_info):       
        InternationalInformation = self.factory.InternationalInformation()
        InternationalInformation.DocumentsOnlyIndicator = 'False'#Boolean #Optional.Indicates documents only. If selected, no other international information is required.
        ContentDetails = []#Required if sending International shipment. Details of shipment for customs. #Complex Type ContentDetail
        for line in so_lines:
            if line.is_delivery == False:
                ContentDetail = self.factory.ContentDetail()
                ContentDetail.Description = line.product_id.name#String#Required if sending US/International shipment, and not Documents only. Description of contents.
                ContentDetail.HarmonizedCode = line.product_id.hs_code.replace("-","").replace(".","") #String# Required if sending US/International shipment, and not Documents only Harmonized code for item.
                ContentDetail.CountryOfManufacture = line.product_id.product_tmpl_id.country_of_manufacture.code if line.product_id.product_tmpl_id.country_of_manufacture != False else ''#String#Required if sending US/International shipment, and not Documents only. Country of manufacture of item.
                ContentDetail.ProductCode = line.product_id.default_code.replace("[","").replace("]","") if line.product_id.default_code != False else ''##String#Required if sending US/International shipment, and not Documents only. Products code of item.
                ContentDetail.UnitValue = line.price_unit#String# Required if sending US/International shipment, and not Documents only. Unit Value of item.
                ContentDetail.Quantity =  line.product_qty#String#Required if sending US/International shipment, and not Documents only. Quantity of item.
                ContentDetail.NAFTADocumentIndicator = str(NAFTA)#xsd:boolean, l#Required if sending US/International shipment, and not Documents only. Indicator to generate NAFTA documentation.
                ContentDetail.FDADocumentIndicator = str(FDA)#xsd:boolean
                ContentDetail.FCCDocumentIndicator = str(FCC)#xsd:boolean,  #Required if sending US/International shipment, and not Documents only.
                ContentDetail.SenderIsProducerIndicator = True if self.Shipment.SenderInformation.Address.Country == line.product_id.product_tmpl_id.country_of_manufacture.code else False# str(SIPI)#xsd:boolean, #Required if sending US/International shipment, and not Documents only.
                ContentDetail.TextileIndicator = str(Textile)#Bool#Optional.Required if sending textile products to the U.S.
                ContentDetail.TextileManufacturer = str(TextileMan)#Max. 250 chracters#Bool#Required if TextileIndicator is set to true.
                ContentDetails.append(ContentDetail)

        InternationalInformation.ContentDetails = ContentDetails
        BuyerInformation = self.factory.BuyerInformation()
        BuyerAddress  = self.factory.Address()
        if buyer =='same':
            BuyerAddress = self.Shipment.ReceiverInformation.Address
            BuyerInformation.Address = BuyerAddress#Complex Type Address
            BuyerInformation.TaxNumber = buyer_info.vat#Optional. Tax Number# String Alpha Numeric
        elif buyer =='diff':
            if buyer_info.is_company:
                BuyerAddress.Name = buyer_info.name
                BuyerAddress.Company = buyer_info.name
            else:
                BuyerAddress.Name = buyer_info.name
                BuyerAddress.Company = buyer_info.parent_id.name or ''
            if buyer_info.street == False and buyer_info.street2 == False:
                BuyerAddress.StreetName = None
            elif buyer_info.street2 == False:
                BuyerAddress.StreetName = buyer_info.street
            elif buyer_info.street == False:
                BuyerAddress.StreetName = buyer_info.street2
            else:
                BuyerAddress.StreetName = buyer_info.street + buyer_info.street2
            BuyerAddress.City = buyer_info.city or ''
            if buyer_info.country_id.code in STATECODE_REQUIRED_COUNTRIES:
                BuyerAddress.Province = buyer_info.state_id.code or ''
            else:
                BuyerAddress.Province  = ''
            BuyerAddress.Country = buyer_info.country_id.code or ''
            BuyerAddress.PostalCode = buyer_info.zip.replace(" ","") if buyer_info.zip != False else ''
            BuyerPhoneNumber = self.factory.PhoneNumber()
            rcv_phone_or = buyer_info.phone.replace('-','').replace('(','').replace(')','') if buyer_info.phone != False else buyer_info.phone
            
            rcv_phone_sp = rcv_phone_or.replace(' ','') if rcv_phone_or != False else False  
            if rcv_phone_sp != False:
                # rcv_phone_cn_code = rcv_phone_sp[0] if len(rcv_phone_sp) > 1  else "+"+ str(buyer_info.country_id.phone_code)
                # if len(rcv_phone_sp) > 1:
                #     rcv_arr = rcv_phone_sp[1]
                # else:
                #     rcv_arr = rcv_phone_sp[0]
                # rcv_phone_ar_code = rcv_arr[-10:-7] if len(rcv_arr) > 3 else False
                # rcv_phone = rcv_arr[-7:] if len(rcv_arr) > 3 else False
                rcv_phone_cn_code = rcv_phone_sp[:-10] if len(rcv_phone_sp) > 1  else "+"+ str(recipient_partner.country_id.phone_code)
                rcv_phone_ar_code = rcv_phone_sp[-10:-7] if len(rcv_phone_sp) > 3 else False
                rcv_phone = rcv_phone_sp[-7:] if len(rcv_phone_sp) > 3 else False
            else:
                rcv_phone_cn_code = "+"+ str(buyer_info.country_id.phone_code) if len(buyer_info.country_id) > 0 else ''
                rcv_phone_ar_code = ''
                rcv_phone = ''
            BuyerPhoneNumber.CountryCode = rcv_phone_cn_code
            BuyerPhoneNumber.AreaCode = rcv_phone_ar_code
            BuyerPhoneNumber.Phone = rcv_phone
            BuyerAddress.PhoneNumber = BuyerPhoneNumber
            BuyerInformation.Address = BuyerAddress
            self.Shipment.BuyerInformation = BuyerInformation

        InternationalInformation.BuyerInformation = BuyerInformation
        InternationalInformation.PreferredCustomsBroker = ''#'US551-ACCENT'#stringOptional. For US ground shipments only.
        DutyInformation = self.factory.DutyInformation()
        DutyInformation.BillDutiesToParty = 'Buyer'# Enumeration:  # • Sender • Receiver • Buyer Optional (required if sending US/Intl shipment) Specifies where duty charges (if any) should be billed to.
        DutyInformation.BusinessRelationship = 'NotRelated'#Enumeration: • Related • NotRelated# Optional (required if sending= US/Intl shipment) Relationship  of company/person that duty is charged to.
        DutyInformation.Currency = 'CAD'#Enumeration:• CAD • USD Optional (required if sending US/Intl shipment) Currency of duty.
        InternationalInformation.DutyInformation = DutyInformation
        InternationalInformation.ImportExportType ='Permanent'#Enumeration: Permanent Temporary Repair Return
        InternationalInformation.CustomsInvoiceDocumentIndicator = 'False'#Bool #Required if sending International shipment.
        self.Shipment.InternationalInformation = InternationalInformation

    ###NotificationInformation
    def set_email_notify(self, email1, email2): 
        NotificationInformation = self.factory.NotificationInformation()
        if email1 != '':
            NotificationInformation.ConfirmationEmailAddress = email1 if email1 != '' else '' 
        if email2 != '':
            NotificationInformation.AdvancedShippingNotificationEmailAddress1 = email2# Optional.
        self.Shipment.NotificationInformation = NotificationInformation

    #Label Stuff
    def start_label_transaction(self, wsdl_path,purolator_activation_key):
        settings = Settings(strict=False)
        self.client = Client('file:///%s' % wsdl_path.lstrip('/'), plugins=[LogPlugin(self.debug_logger)], settings=settings)
        self.factory = self.client.type_factory('ns1')
        RequestContext = {
                'Version': '1.3',
                'Language': 'en',
                'GroupID': 'Syncoria Client',
                'RequestReference': 'Syncoria Client',      
            }
        if not self.prod_environment:
            RequestContext['UserToken'] = purolator_activation_key
        self.RequestContext = RequestContext

    def get_label_url(self, TrackingPIN, FileFormat):
        # print("gget_label_urlet")
        self.ArrayOfDocumentCriteria = self.factory.ArrayOfDocumentCriteria()
        DocumentCriteria = self.factory.DocumentCriteria()
        PIN = self.factory.PIN()
        PIN.Value = TrackingPIN
        DocumentCriteria.PIN = PIN
        self.ArrayOfDocumentCriteria.DocumentCriteria = DocumentCriteria
        self.DocumentTypes = 'DomesticBillOfLadingThermal'
        response = self.client.service.GetDocuments(FileFormat,False,self.ArrayOfDocumentCriteria,
                        _soapheaders={'RequestContext': self.RequestContext})
        LABEL_URLS =[]
        if len(response.body.ResponseInformation.Errors.Error) == 0:
            for label in response.body.Documents.Document:                
                LABEL_URLS.append(label.DocumentDetails.DocumentDetail[0].URL)
            return {'error': None, 'url': LABEL_URLS}
        else:
            return {'error': True, 'url':''}
        # print(LABEL_URLS)

    def set_soapheaders(self, wsdl_path,purolator_activation_key):
        settings = Settings(strict=False)
        self.client = Client('file:///%s' % wsdl_path.lstrip('/'), plugins=[LogPlugin(self.debug_logger)], settings=settings)
        self.factory = self.client.type_factory('ns1')
        RequestContext = {
                'Version': '2.0',
                'Language': 'en',
                'GroupID': 'Syncoria Client',
                'RequestReference': 'Syncoria Client', 
            }
        if not self.prod_environment:
            RequestContext['UserToken'] = purolator_activation_key
        self.RequestContext = RequestContext

    #TrackPackagesByPin
    def trackpackage_bypin(self,carrier_tracking_ref):
        formatted_response = {'tracking_number': 0.0,
                              'price': {},
                              'master_tracking_id': None,
                              'date': None}
        try:
            PINs = []
            PIN = self.factory.PIN()
            PIN.Value = carrier_tracking_ref
            PINs.append(PIN)
            self.response = self.client.service.TrackPackagesByPin(PINs, _soapheaders={'RequestContext':self.RequestContext})
            if self.response.body.ResponseInformation.Errors == None:
                formatted_response['master_tracking_id'] = self.response.body.ShipmentPIN.Value
            else:
                errors_message='Shipment Creation Error:'
                errors_message = '\n'.join([("%s: %s" % (n.Code, n.Description)) for n in self.response.body.ResponseInformation.Errors.Error if response2.body.ResponseInformation.Errors != None])
                formatted_response['errors_message'] = errors_message
        except Fault as fault:
            formatted_response['errors_message'] = fault
        except IOError:
            formatted_response['errors_message'] = "Purolator Server Not Found"
        except Exception as e:
            formatted_response['errors_message'] = e.args[0]
        return formatted_response