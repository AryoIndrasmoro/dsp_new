# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields,osv
from datetime import datetime
import openerp.addons.decimal_precision as dp
#from openerp.tools.translate import _

class product_grape(osv.osv):
    _name = 'product.grape'
    _columns = {'name': fields.char('Name', size=128)}
product_grape() 

class product_brand(osv.osv):
    _name = 'product.brand'
    _columns = {'name': fields.char('Name', size=128)}
product_brand()

class product_region(osv.osv):
    _name = 'product.region'
    _columns = {
                'name': fields.char('Name', size=30),
                'preface': fields.text('Preface')
                }
product_region()

class product_type(osv.osv):
    _name = 'product.type'
    _columns = {'name': fields.char('Name', size=128)}
product_type()   

class product_appelation(osv.osv):
    _name = 'product.appelation'
    _columns = {'name': fields.char('Name', size=128)}
product_appelation() 

class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        #'vintages': fields.boolean('Outlets/Customers', help="Check this box if this contact is a customer / outlet."),                                                        
    }
    
    _defaults = {        
        'cost_method'   : 'average',        
        'valuation'     : 'manual_periodic',
        'type'          : 'product',        
    }
    
    #===========================================================================
    # def action_view_all_products(self, cr, uid, ids, context=None):        
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Product List', 
    #         'view_type': 'tree',
    #         'view_mode': 'tree',
    #         'res_model': 'product.product',            
    #         'target': 'new',
    #         'nodestroy' : True,
    #     }
    #===========================================================================
        
    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []
        def _name_get(d):
            name = d.get('name','')
            code = d.get('default_code',False)
            vintage = d.get('vintages',False)
            foc = d.get('foc',False)            
            if code:
                name = '[%s] %s' % (code,name)
            if vintage:
                name = name + ' - ' + str(vintage)
            
            if foc == 'FOC':
                name = name + ' - FOC'
            #else:
            #    name = name + ' - NV'
            if d.get('variants'):
                name = name + ' - %s' % (d['variants'],)
            return (d['id'], name)
 
        partner_id = context.get('partner_id', False)
 
        result = []
        for product in self.browse(cr, user, ids, context=context):
            sellers = filter(lambda x: x.name.id == partner_id, product.seller_ids)
            if sellers:
                for s in sellers:
                    mydict = {
                              'id': product.id,
                              'name': s.product_name or product.name,
                              'default_code': s.product_code or product.default_code,
                              'variants': product.variants,
                              'vintages': product.vintages,
                              'foc' : product.foc
                              }
                    result.append(_name_get(mydict))
            else:
                mydict = {
                          'id': product.id,
                          'name': product.name,
                          'default_code': product.default_code,
                          'variants': product.variants,
                          'vintages': product.vintages,
                          'foc' : product.foc
                          }
                result.append(_name_get(mydict))
        return result
    
product_product()

class product_template(osv.osv):
    _inherit = "product.template"
    _description = "Product Template"
    
    def _compute_suggest_price(self, cr, uid, ids, field_names, args, context=None):
        print """Compute the amounts in the currency of the user
        """
        if context is None:
            context={}
        res = {}
        for product in self.browse(cr, uid, ids, context=context):            
            jkt_cost       = product.jkt_cost                       
            margin          = product.jkt_cost * (product.margin/ 100)
            suggest_price   = jkt_cost + margin                
            res[product.id] = {
                    'suggest_price' : suggest_price,
                    'real_price'    : suggest_price,
                        }
        return res
    
    def _compute_reserved_qty(self, cr, uid, ids, field_names, args, context=None):
        print """Compute the amounts in the currency of the user
        """
        total_reserved = 0.0
        if context is None:
            context={}
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            for reserved in product.qty_reserved:
                total_reserved += reserved.reserved_qty
                print total_reserved
                                            
            res[product.id] = total_reserved
        return res
    
    _columns = {
            'name'              : fields.char('Name', size=128, required=True, translate=True, select=True, change_default=True),
            'vintages'          : fields.selection([(num, str(num)) for num in range(1970, (datetime.now().year) )], 'Vintages', store='True'),
            'classification'    : fields.char('Classification', size=128),        
            'grape_id'          : fields.many2one('product.grape', 'Grape', required=False, ondelete='cascade', help="Product Grape."),   
            'country_id'        : fields.many2one('res.country', 'Country', required=False, ondelete='cascade', help="Product Country."),
            'region_id'         : fields.many2one('product.region', 'Region', required=False, ondelete='cascade', help="Product Region."),  
            'type_id'           : fields.many2one('product.type', 'Type', required=False, ondelete='cascade', help="Product Type."),   
            'appelation_id'     : fields.many2one('product.appelation', 'Appelation', required=False, ondelete='cascade', help="Product Appelation."),            
            'brand'             : fields.many2one('product.brand', 'Brand', required=False, ondelete='cascade'),
            'volume_l'          : fields.float('Volume (L)', digits_compute=dp.get_precision('Product Price')),
            'volume_alcohol'    : fields.float('Volume Alcohol (%)', digits_compute=dp.get_precision('Product Price')),
            'foc'               : fields.selection([('FOC', 'FOC'),('Regular', 'Regular')], 'FOC'),
            'jkt_cost'          : fields.float('JKT Cost', digits_compute=dp.get_precision('Product Price')),
            'base_cost'         : fields.float('SG Cost', digits_compute=dp.get_precision('Product Price')),
            'margin'            : fields.float('Margin (%)', digits_compute=dp.get_precision('Product Price')),
            'suggest_price'     : fields.function(_compute_suggest_price, string="Suggested Price", type='float', digits_compute=dp.get_precision('Product Price'), multi="_compute_amounts"),                            
            'real_price'        : fields.float('Product Real Price', digits_compute=dp.get_precision('Product Price')),
            'qty_reserved'      : fields.one2many('product.reserved.qty', 'product_id', 'Qty Reserved'),
            'total_reserved'    : fields.function(_compute_reserved_qty, string="Reserved Qty", type='float', digits_compute=dp.get_precision('Product Unit of Measure')),                         
            #'real_price'    : fields.function(_compute_suggest_price, string="Real Price", type='float', digits_compute=dp.get_precision('Account'), multi="_compute_amounts"),
                }
    
    _defaults = {        
        'foc'   : 'Regular',                    
    }
product_template()

class product_reserved_qty(osv.osv):
    _name = "product.reserved.qty"
    _description = "Product Reserved Qty"            
    
    _columns = {
            'product_id'        : fields.many2one('product.product', 'Product'),
            'outlet'            : fields.many2one('res.partner', 'Outlet', required=True, domain=[('customer','=',True)]),
            'reserved_qty'      : fields.float('Reserved Qty', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
            'reserved_date'     : fields.date('Reserved Date', required=True),                
            'delivery_date'     : fields.date('Delivery Date'),               
        }                        
product_reserved_qty()