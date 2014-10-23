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
    'name' : 'PDBI CRM Module',
    'version' : '1.0',
    'author' : 'Futuratechgroup',
    'category' : 'CRM',
    'description' : 'PDBI CRM Customization Module',
    'website': 'http://www.futuratechgroup.com',
    'depends' : ['base','purchase','stock','product','account','account_voucher','sale','sale_crm','report_webkit'],
    'data': [        
             'view/res_partner_view.xml',                
            ],
    #'update_xml': ['sale_analysis_report.xml'],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
