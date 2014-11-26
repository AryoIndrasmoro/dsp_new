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

class cash_report_bag(osv.osv):
    _name = "cash.report.bag"
    _description = "Cash Report Statistics"
    _auto = False
    #_rec_name = 'date'
    _columns = {
        'id': fields.text('ID', readonly=True),
        'date': fields.date('Date', readonly=True),
        'description': fields.text('Title', readonly=True),
        'type': fields.text('Type', readonly=True),
        'amount': fields.float('Amount'),
        'category': fields.text('Category', readonly=True),
        'created_by': fields.text('Created By', readonly=True),               
    }
    #_order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'cash_report_bag')
        cr.execute("""
            create or replace view cash_report_bag as (
                select                    
                    id,
                    date,
                    type,
                    description,
                    category,
                    created_by,
                    amount      
                from
                    kas_bag                                                    
            )
        """)
cash_report_bag()

class receivable_report_bag(osv.osv):
    _name = "receivable.report.bag"
    _description = "Receivable Report Statistics"
    _auto = False
    #_rec_name = 'date'
    _columns = {
        'id': fields.text('ID', readonly=True),
        'date': fields.date('Date', readonly=True),
        'description': fields.text('Title', readonly=True),
        'type': fields.text('Type', readonly=True),
        'amount': fields.float('Amount'),
        'category': fields.text('Category', readonly=True),
        'created_by': fields.text('Created By', readonly=True),          
    }
    #_order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'receivable_report_bag')
        cr.execute("""
            create or replace view receivable_report_bag as (
                select                    
                    id,
                    date,
                    type,
                    description,
                    category,
                    created_by,
                    amount            
                from
                    receivable_bag                                                    
            )
        """)
receivable_report_bag()

class payable_report_bag(osv.osv):
    _name = "payable.report.bag"
    _description = "Payable Report Statistics"
    _auto = False
    #_rec_name = 'date'
    _columns = {
        'id': fields.text('ID', readonly=True),
        'date': fields.date('Date', readonly=True),
        'description': fields.text('Title', readonly=True),
        'status': fields.text('Status', readonly=True),        
        'amount': fields.float('Amount'),           
        'customer_id': fields.text('Customer', readonly=True),             
    }
    #_order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'payable_report_bag')
        cr.execute("""
            create or replace view payable_report_bag as (
                select                    
                    b.id,
                    b.date,                    
                    b.description,                                        
                    b.amount,
                    b.status,
                    p.name as customer_id            
                from
                    payable_bag b
                    join res_users u on u.id = b.customer_id
                    join res_partner p on p.id = u.partner_id 
            )
        """)
payable_report_bag()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
