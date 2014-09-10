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
{
    'name' : 'DSP Openerp Module',
    'version' : '1.0',
    'author' : 'Futuratechgroup',
    'category' : 'Wine Distributor',
    'description' : """
DSP OpenERP Customization Module.
====================================

This module covers: test
--------------------------------------------
    * Sales
    * CRM
    * Purchase
    * Warehouse
    * Customer and Supplier Invoices
    * Customer and Supplier Payments
    """,
    'website': 'http://www.futuratechgroup.com',
    'depends' : ['base','purchase','stock','product','account','account_voucher','sale','sale_crm','report_webkit'],
    'data': [
        'view/product_view.xml',
        'view/account_invoice_view.xml',
        'view/account_menuitem.xml',
        'view/account_view.xml',
        'view/voucher_payment_receipt_view.xml',
        'view/res_partner_view.xml',
        'view/sale_crm_view.xml',
        'view/stock_view.xml',
        'view/purchase_view.xml',        
        'view/sale_view.xml',                
        'report/sale_report_view.xml',
        'stock_view_report.xml',               
        
    ],
    #'update_xml': ['sale_analysis_report.xml'],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
