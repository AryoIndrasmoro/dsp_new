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

class pricelist_report(osv.osv):
    _name = "pricelist.report"
    _description = "Price list Statistics"
    _auto = False
    #_rec_name = 'date'
    _columns = {
        'id': fields.text('Date Order', readonly=True),
        'name_template': fields.text('Date Order', readonly=True),
        'volume_l': fields.text('Date Order', readonly=True),
    }
    #_order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'pricelist_report')
        cr.execute("""
            create or replace view pricelist_report as (
                select
                    id,
                    name_template,
                    volume_l
                from
                    product_product

            )
        """)
pricelist_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
