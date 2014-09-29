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

from openerp import tools
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp

class pricelist_report(osv.osv):
    _name = "pricelist.report"
    _description = "Price list Statistics"
    _auto = False
    #_rec_name = 'date'
    _columns = {
        'id': fields.text('Date Order', readonly=True),
        'name': fields.char('Order No', readonly=True),        
        'sale_type': fields.char('Sale Type', readonly=True),
        'date_order': fields.date('Date Order', readonly=True),
        'amount_total': fields.float('Amount Total', digits_compute=dp.get_precision('Product Price'), readonly=True),
        'qty': fields.float('Qty', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'partner_name': fields.char('Outlet', readonly=True),
        'product_name': fields.char('Product', readonly=True),
        'product_type': fields.char('Product Type', readonly=True),
    }
    #_order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'pricelist_report')
        cr.execute("""
            create or replace view pricelist_report as (
                select
                    p.name_template as product_name,
                    pt.foc as product_type,
                    s.id,
                    s.name,
                    s.sale_type,
                    s.date_order,
                    s.amount_total,                    
                    sl.product_uom_qty as qty,
                    r.name as partner_name
                from
                    sale_order s, 
                    sale_order_line sl, 
                    product_product p, 
                    product_template pt,
                    res_partner r
                where 
                    sl.order_id = s.id and
                    sl.product_id = p.id and                            
                    sl.product_id = pt.id and
                    s.partner_id = r.id
            )
        """)
pricelist_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
