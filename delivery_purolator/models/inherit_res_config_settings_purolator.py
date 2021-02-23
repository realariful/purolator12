from ast import literal_eval
from odoo import api, fields, models

class ResConfigSettingsForPurolator(models.TransientModel):
    _inherit = 'res.config.settings'

    module_delivery_purolator = fields.Boolean("Purolator")