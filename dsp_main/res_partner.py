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
import openerp.addons.decimal_precision as dp
#from openerp.tools.translate import _

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'customer': fields.boolean('Outlets/Customers', help="Check this box if this contact is a customer / outlet."),        
        'discount': fields.selection([(5, '5'),(10,'10'),(15,'15'),(20,'20'),(25,'25'),(30,'30') ], 'Incentive Discount (%)'),
        'dsp_price_list_id' : fields.selection([('standard', 'Suggest Price'), ('real', 'Real Price'), ('outlet', 'Outlet Price')], 'DSP Price List', invisible="1"),
        'outlet_margin'     : fields.float('Outlet Margin (%)', digits_compute=dp.get_precision('Product Price')),
        'bypass_order'      : fields.boolean('Bypass Order', help="Check this box if this this outlet allowed to order in outstanding payment status"),
    }
    
    _defaults = {
            'dsp_price_list_id' : 'standard',
            'bypass_order'      : False,
                 }

res_partner()
