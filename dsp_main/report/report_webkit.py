import time
from openerp.report import report_sxw
from openerp.osv import osv
import openerp.pooler

class Session(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Session, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        }) 
class report_webkit_html(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_webkit_html, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            #'get_data': self._get_data,
            })
        
    #def _get_data(self,data):
    #    print "data",data
    #    return self.pool.get(data['model']).browse(self.cr,self.uid,[data['id']]) 
    
#report_sxw.report_sxw('report.openacademy.session', 'openacademy.session', 'addons/openacademy_training/report/report_session.rml', parser = Session, header = "internal landscape")
#report_sxw.report_sxw('report.openacademy.session.webkit', 'openacademy.session', 'addons/openacademy_training/report/report_session.mako', parser = Session, header = False)
report_sxw.report_sxw('report.stock.list.out.webkit.dsp',
                       'stock.picking.out', 
                       'dsp/report/delivery_slip.mako',
                       parser=report_webkit_html)