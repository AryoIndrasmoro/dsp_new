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
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
#from openerp.tools.translate import _

class kas_bag(osv.osv):
    _name = "kas.bag"    
    _columns = {
            'number'            : fields.char('Transaction No'),
            'date'              : fields.date('Date'),
            'type'              : fields.selection([('Money In','Money In'),('Money Out','Money Out')],'Type'),
            'description'       : fields.char('Title'),
            'amount'            : fields.float('Amount (IDR)'),
            'category'          : fields.selection([('Credit','Credit'),('Cash','Cash'),('Income','Income'),('Sales','Sales'),('Transfer','Transfer')],'Category'),
            'created_by'        : fields.many2one('res.users', 'Created By', select=True, track_visibility='onchange'),                    
                }
    
    _defaults = {
                 'date' : lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
                 'created_by' : lambda obj, cr, uid, context: uid,
                 }        
kas_bag()

class receivable_bag(osv.osv):
    _name = "receivable.bag"    
    _columns = {
            'number'            : fields.char('Transaction No'),
            'date'              : fields.date('Due Date'),
            'type'              : fields.selection([('Money In','Money In'),('Money Out','Money Out')],'Type'),
            'description'       : fields.char('Title'),
            'amount'            : fields.float('Amount (IDR)'),
            'category'          : fields.selection([('Credit','Credit'),('Cash','Cash'),('Income','Income'),('Sales','Sales'),('Transfer','Transfer')],'Category'),
            'created_by'        : fields.many2one('res.users', 'Created By', select=True, track_visibility='onchange'),                    
                }
            
    _defaults = {
                 'type' : 'Money In',
                 'date' : lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
                 'created_by' : lambda obj, cr, uid, context: uid,
                 }
receivable_bag()  

class payable_bag(osv.osv):
    _name = "payable.bag"    
    _columns = {
            'number'            : fields.char('Transaction No'),
            'date'              : fields.date('Due Date'),            
            'description'       : fields.char('Description'),
            'amount'            : fields.float('Amount'),    
            'status'            : fields.selection([('Pending','Pending'),('Paid','Paid')],'Status'),
            'customer_id'       : fields.many2one('res.users','Customer', select=True, track_visibility='onchange'),                
                }
    
    _defaults = {
                 'status' : 'Pending',                 
                 }
            
payable_bag()    