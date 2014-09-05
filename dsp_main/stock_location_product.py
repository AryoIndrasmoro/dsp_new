import logging

from openerp.osv import fields, osv
from openerp.tools.translate import _
import time
import pdb


_logger = logging.getLogger(__name__)

class stock_location_product(osv.osv_memory):
    _inherit = "stock.location.product"
    
    def action_open_window(self, cr, uid, ids, context=None):
        
        
        if context is None:
            context = {}
        location_products = self.read(cr, uid, ids, ['from_date', 'to_date'], context=context)
        # GET Location Name : Edited On 1 August by Adithia
        result = self.pool['stock.location'].browse(cr, uid, context['active_id'], context=context)

        
        if location_products:
            return {
    
                'name': _('Current Inventory -- %s -- %s') % (result.location_id.name, result.name),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'product.product',
                'type': 'ir.actions.act_window',
                'context': {'location': context['active_id'],
                       'from_date': location_products[0]['from_date'],
                       'to_date': location_products[0]['to_date']},
                'domain': [('type', '<>', 'service')],
            } 
        
stock_location_product()
            