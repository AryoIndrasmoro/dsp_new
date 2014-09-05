from openerp import tools
from openerp.osv import fields, osv

class sale_report(osv.osv):
    _inherit = 'sale.report'
    _columns = {
                'discount': fields.float('Discount')
                }
sale_report()    