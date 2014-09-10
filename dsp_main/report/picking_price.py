##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import time
from report import report_sxw
from osv import osv,fields
from report.render import render
#from ad_num2word_id import num2word
import pooler
#from report_tools import pdf_fill,pdf_merge
from tools.translate import _
import tools
from tools.translate import _
import decimal_precision as dp
#from ad_amount2text_idr import amount_to_text_id
#from tools import amount_to_text_en        

class picking_price(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(picking_price, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_product_desc': self.get_product_desc,
            'get_total_qty': self.get_total_qty,
            'get_total_amount': self.get_total_amount,                        
        })
    def get_product_desc(self, move_line):
        price = move_line.price_unit * move_line.product_qty
        return price
        
        #=======================================================================
        # desc = move_line.product_id.name
        # if move_line.product_id.default_code:
        #     desc = '[' + move_line.product_id.default_code + ']' + ' ' + desc
        # return desc        
        #=======================================================================

    def get_total_qty(self, picking):
        total_qty = 0
        for line in picking.move_lines:
            total_qty = total_qty + line.product_qty        
        return total_qty
    
    def get_total_amount(self, picking):
        total_amount = 0        
        for line in picking.move_lines:
            price = line.price_unit * line.product_qty
            total_amount = total_amount + price        
        return total_amount        
    
for suffix in ['', '.in', '.out']:
    report_sxw.report_sxw('report.stock.picking.list.price' + suffix,
                          'stock.picking.out' + suffix,
                          'dsp_main/report/picking_price.rml',
                          parser=picking_price, header=False)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
