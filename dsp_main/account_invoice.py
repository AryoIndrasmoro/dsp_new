
import logging
import time
from lxml import etree


from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
                'person_name'           : fields.char('Person Name', size=128),
                'date_confirmed'        : fields.date('Input Date'),
                'file_confirmed'        : fields.binary('Input File'),
                }
        
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        journal_obj = self.pool.get('account.journal')
        if context is None:
            context = {}

        if context.get('active_model', '') in ['res.partner'] and context.get('active_ids', False) and context['active_ids']:
            partner = self.pool.get(context['active_model']).read(cr, uid, context['active_ids'], ['supplier','customer'])[0]
            if not view_type:
                view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'account.invoice.tree')])
                view_type = 'tree'
            if view_type == 'form':
                if partner['supplier'] and not partner['customer']:
                    view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'account.invoice.supplier.form')])
                elif partner['customer'] and not partner['supplier']:
                    view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'account.invoice.form')])
        if view_id and isinstance(view_id, (list, tuple)):
            view_id = view_id[0]
        res = super(account_invoice,self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)

        type = context.get('journal_type', False)
        for field in res['fields']:
            if field == 'journal_id' and type:
                journal_select = journal_obj._name_search(cr, uid, '', [('type', '=', type)], context=context, limit=None, name_get_uid=1)
                res['fields'][field]['selection'] = journal_select

        doc = etree.XML(res['arch'])

        if context.get('type', False):
            for node in doc.xpath("//field[@name='partner_bank_id']"):
                if context['type'] == 'in_refund':
                    node.set('domain', "[('partner_id.ref_companies', 'in', [company_id])]")
                elif context['type'] == 'out_refund':
                    node.set('domain', "[('partner_id', '=', partner_id)]")
            res['arch'] = etree.tostring(doc)

        if view_type == 'search':
            if context.get('type', 'in_invoice') in ('out_invoice', 'out_refund'):
                for node in doc.xpath("//group[@name='extended filter']"):
                    doc.remove(node)
            res['arch'] = etree.tostring(doc)        

        if view_type == 'tree':
            partner_string = _('Outlet/Customer')
            if context.get('type', 'out_invoice') in ('in_invoice', 'in_refund'):
                partner_string = _('Supplier')
                for node in doc.xpath("//field[@name='reference']"):
                    node.set('invisible', '0')
            for node in doc.xpath("//field[@name='partner_id']"):
                node.set('string', partner_string)
            res['arch'] = etree.tostring(doc)
        return res
    
account_invoice()
    