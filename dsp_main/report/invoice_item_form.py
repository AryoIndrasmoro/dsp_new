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

class invoice_item_form(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(invoice_item_form, self).__init__(cr, uid, name, context=context)
      
        self.line_no = 0
        self.localcontext.update({
            'get_object':self._get_object,
            'time': time,
            'convert':self.convert,
            'get_company_address': self._get_company_address,
            #'angka':self.angka,
#            'alamat': self.alamat_npwp,
            'convert':self.convert,
            'convert_idr': self.convert_idr,
            'charge':self.charge,
#            'nourut': self.no_urut,
#            'get_ppn': self.get_ppn,
            'line_no':self._line_no,
            'blank_line':self.blank_line,
            'blank_line_rfq':self.blank_line_rfq,
            'get_grand_total':self.get_grand_total,
#            'get_internal':self._get_internal,
#            'sum_tax':self._sum_tax,
#            'get_curr2':self.get_curr,
#            'get_invoice':self._get_invoice,
#            'get_curr':self._get_used_currency,
        }) 
    
   
    def get_grand_total(self,total,chargeline):
        gt=0
        charge=0
        for line in chargeline:
            charge=+line.amount
        gt=charge+total
        return gt
    
    def charge(self,line):
        cost=0
        for line in line:
            cost=+line.amount
        return cost
    
    def convert(self, amount, cur):
        print "SSSSSSSSSSSSSSSS"
        amt_en = amount_to_text_en.amount_to_text(amount, 'en', cur)
        return amt_en
    
    def convert_idr(self, amount, cur):
        print "RRRRRRRRRRRRRRRR",amount, cur
        amt_en = amount_to_text_id.amount_to_text( amount, cur)
        return amt_en
    
    def _get_object(self,data):
        obj_data=self.pool.get(data['model']).browse(self.cr,self.uid,[data['id']])
        seq=obj_data[0].print_seq
        seq+=1
        obj_data[0].write({'print_seq':seq})
        return obj_data
        
    def blank_line(self, nlines):
        row = len(nlines)
        
        res = ""
        
        if row < 15:
            for i in range(15 - row):
                res = res + ('<tr> <td class="row_line_left">&nbsp;</td> <td class="row_line" colspan="2">&nbsp;</td><td class="row_line">&nbsp;</td><td class="row_line">&nbsp;</td><td class="row_line">&nbsp;</td><td class="row_line_right">&nbsp;</td></tr>')

        return res
    
    def blank_line_rfq(self, nlines):
        row = len(nlines)
        
        res = ""
        
        if row < 15:
            for i in range(15 - row):
                res = res + ('<tr> <td class="row_line_left">&nbsp;</td> <td class="row_line" colspan="2">&nbsp;</td> <td class="row_line">&nbsp;</td> <td class="row_line">&nbsp;</td> </tr>')

        return res
        
    def _get_company_address(self, company):
        partner = company.partner_id.id
        address_id = self.pool.get('res.partner.address').search(self.cr,self.uid,[('partner_id','=',partner)])
        address = self.pool.get('res.partner.address').browse(self.cr,self.uid,address_id[0])
        
        return address
        
    def _line_no(self):
        self.line_no = self.line_no + 1
        return self.line_no
    
    def _blank_line(self, nlines, row, type):
        res = ""
        if type=="IDR":
            if row > 1:
                for i in range(nlines+1):
                    res = res + ('<tr class="sub_line"><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>')
            else:
                for i in range(nlines - row):
                    res = res + ('<tr class="sub_line"><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>')
        else:
            if row > 1:
                for i in range(nlines+1):
                    res = res + ('<tr class="sub_line"><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>')
            else:
                for i in range(nlines - row):
                    res = res + ('<tr class="sub_line"><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>')

        return res

    
    def no_urut(self, list, value):
        return list.index(value) + 1
        


                   
report_sxw.report_sxw('report.invoice.item.form', 'account.invoice', 'dsp_main/report/invoice_item_form.rml', parser=invoice_item_form,header=False)
#report_sxw.report_sxw('report.request.for.quotation.form', 'purchase.order', 'ad_po_form/report/request_for_quotation_form.mako', parser=purchase_order_form,header=False)


