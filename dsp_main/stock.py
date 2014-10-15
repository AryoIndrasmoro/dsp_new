from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import pytz
from operator import itemgetter
from itertools import groupby

from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
import logging
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP


class stock_picking(osv.osv):
    #_name = "stock.picking.in"
    _inherit = "stock.picking"    
    _columns = {
            'journal_id'            : fields.many2one('account.journal', 'Bank/ Cash'),
            'cost_component_line'   : fields.one2many('cost.component', 'picking_id', 'Contains'),
            'additional_cost'       : fields.selection([('no','Non Cost Component'), ('yes','With Cost Component')], 'Cost Component', readonly=False),
            'person_name'           : fields.char('Person Name', size=128),
            'date_confirmed'        : fields.date('Input Date'),
            'file_confirmed'        : fields.binary('Delivery Slip before Deliver'),
            'notes_picking'         : fields.text('Delivery Notes'),
            'additional_cost_int'   : fields.selection([('no','Without Cost Component'), ('yes','With Cost Component')], 'Cost Component', readonly=False),
            'internal_move_type'    : fields.selection([('overseas','Overseas'), ('regular','Regular'), ('consignment','Consignment')], 'Move Type'),
            'person_name_ex'        : fields.char('Person Name', size=128),
            'date_confirmed_ex'     : fields.date('Input Date'),
            'file_confirmed_ex'     : fields.binary('Delivery Slip after Deliver'),
            'notes_ex'              : fields.text('Notes'),
            'sale_ref'              : fields.many2one('sale.order', 'Sale Reference'),
            'consignment'           : fields.char('Sale Type'),
            'sale_warehouse'        : fields.char('Warehouse'),
            'sales_person'          : fields.char('Sales Person'),            
                }                
        
    # FIXME: needs refactoring, this code is partially duplicated in stock_move.do_partial()!    
    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        print "Picking In>>>>>>>>>>>>>>>>>>>>>."
        """ Makes partial picking and moves done.
        @param partial_datas : Dictionary containing details of partial picking
                          like partner_id, partner_id, delivery_date,
                          delivery moves with product_id, product_qty, uom
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        else:
            context = dict(context)
        res = {}
        price_idr = 0.0
        foc_qty = 0.0
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        sequence_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids, context=context):            
            new_picking = None
            print "pick type ", pick.type
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, product_avail, partial_qty, product_uoms = {}, {}, {}, {}, {}
            
            # create validation for confirmation
            # if not pick.person_name or not pick.date_confirmed or not pick.file_confirmed:
                # raise osv.except_osv(_('Warning Confirmation !'), _('Please complete the fields of Confirmation tab form!"'))
                #-------------------------------------------------- return False
            #------------------------------------------------------------- else:
            self.dsp_send_email(cr, uid, pick.id, pick.id, context=context)                
            
            # Create Cost Component Journal
            total_credit = 0.0
            if pick.type in ['in','internal']:
                                
                move_pool = self.pool.get('account.move')
                move_line_pool = self.pool.get('account.move.line')
                
                if pick.additional_cost == 'yes' or pick.additional_cost_int == 'yes':            
                    seq = sequence_obj.get_id(cr, uid, pick.journal_id.sequence_id.id)
            
                    period_search = self.pool.get('account.period').search(cr, uid, [('date_start','<=',pick.date),('date_stop','>=',pick.date)])
                    period_browse = self.pool.get('account.period').browse(cr, uid, period_search)
            
                    print "pick.journal_id.id", pick.journal_id.id
                
                    move = {
                            'name'          : seq or '/',
                            'journal_id'    : pick.journal_id.id,
                            'narration'     : pick.purchase_id.name,
                            'date'          : pick.date,
                            'ref'           : pick.purchase_id.name,
                            'period_id'     : period_browse[0].id,
                            'partner_id'    : False
                            }
                
                    move_id = move_pool.create(cr, uid, move)
                            
                    for cost_component_line in pick.cost_component_line:
                    #print "+++++++++++++++++++++", cost_component_line.name or '/'
                        debit = cost_component_line.quantity * cost_component_line.amount
                        move_line = {
                                     'name'      : cost_component_line.name or '/',
                                     'debit'     : debit,
                                     'credit'    : 0.0,
                                     'account_id': cost_component_line.account_id.id,
                                     'move_id'   : move_id,
                                     'journal_id': pick.journal_id.id,
                                     'period_id' : period_browse[0].id,
                                     'partner_id': False,
                                     #'currency_id': 13,
                                     #'amount_currency': company_currency <> current_currency and -bts.amount or 0.0,
                                     'date'      : pick.date,
                                }
                        total_credit += debit
                        move_line_pool.create(cr, uid, move_line)
                
                        #print "total_credit", total_credit
                        move_line = {
                                     'name'      : seq or '/',
                                     'debit'     : 0.0,
                                     'credit'    : debit,
                                     'account_id': pick.journal_id.default_credit_account_id.id,
                                     'move_id'   : move_id,
                                     'journal_id': pick.journal_id.id,
                                     'period_id' : period_browse[0].id,
                                     'partner_id': False,
                                     #'currency_id': 13,
                                     #'amount_currency': company_currency <> current_currency and -bts.amount or 0.0,
                                     'date'      : pick.date,
                                }
                        move_line_pool.create(cr, uid, move_line)
                        
                        move_pool.post(cr, uid, [move_id], context={})
                            
                for move in pick.move_lines:                                        
                    if pick.type == "in":
                        purchase_obj_id = self.pool.get('purchase.order.line').search(cr, uid, [('order_id','=',pick.purchase_id.id),('product_id','=',move.product_id.id)])
                        purchase_obj = self.pool.get('purchase.order.line').browse(cr, uid, purchase_obj_id, context=None)                                    
                        price_idr = purchase_obj[0].price_idr                                                                     
                                                                
                    if move.state in ('done', 'cancel'):
                        continue
                    partial_data = partial_datas.get('move%s' % (move.id), {})                                    
                    product_qty = partial_data.get('product_qty', 0.0)
                    move_product_qty[move.id] = product_qty
                    product_uom = partial_data.get('product_uom', False)
                    product_price = partial_data.get('product_price', 0.0)
                    if product_price == 0:
                        foc_qty = product_qty                    
                    product_currency = partial_data.get('product_currency', False)
                    prodlot_id = partial_data.get('prodlot_id')
                    prodlot_ids[move.id] = prodlot_id
                    product_uoms[move.id] = product_uom
                    partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty, move.product_uom.id)
                    if move.product_qty == partial_qty[move.id]:
                        complete.append(move)
                    elif move.product_qty > partial_qty[move.id]:
                        too_few.append(move)
                    else:
                        too_many.append(move)
                    print "foc_qty ", foc_qty                            
                                        
                    # Average price computation                               
                    if (pick.type == 'in') and (move.product_id.cost_method == 'average'):
                        print "masuk"
                        product = product_obj.browse(cr, uid, move.product_id.id)
                        move_currency_id = move.company_id.currency_id.id
                        context['currency_id'] = move_currency_id
                        qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)
                        qty = qty - foc_qty
                        
                        print "this is the real qty ", qty
                        if product.id in product_avail:
                            product_avail[product.id] += qty
                        else:
                            product_avail[product.id] = product.qty_available
    
                        if qty > 0:
                            new_price = currency_obj.compute(cr, uid, product_currency,
                                    move_currency_id, price_idr)
                            new_price = uom_obj._compute_price(cr, uid, product_uom, new_price,
                                    product.uom_id.id)
                            new_price = price_idr
                            #if product.qty_available <= 0:
                            print "masuk 2"
                            if product.qty_available < 0:
                                print "masuk 3"
                                new_std_price = new_price
                            else:
                                print "masuk 4"
                                # Get the standard price                            
                                amount_unit = product.price_get('standard_price', context=context)[product.id]
                                new_std_price = ((amount_unit * product_avail[product.id])\
                                    + (price_idr * qty)) / (product_avail[product.id] + qty)
                                
                                print "aaaaaaaa", amount_unit
                                print "bbbbbbbb", product_avail[product.id]
                                print "cccccccc", qty
                                print "dddddddd", new_price                            
                                print "new price", new_std_price
                                # Cost Component
                                
                                if pick.additional_cost == 'yes':
                                    print "masuk 5"
                                    #########Change
                                    #cr.execute("select sum(product_qty) from stock_move where picking_id = %s" % pick.id)
                                    #total_qty = cr.fetchone()[0]
                                    
                                    ### Total Partial Data
                                    total_qty = 0.0
                                    for move in pick.move_lines:
                                        partial_data = partial_datas.get('move%s' % (move.id), {})
                                        product_qty = partial_data.get('product_qty', 0.0)                                    
                                        product_id = partial_data.get('product_id', False)
                                        prod = product_obj.browse(cr, uid, product_id)                                                            
                                        if prod.foc == 'Regular':                                                                                                    
                                            total_qty += product_qty
                                    
                                    print "total qty ", total_qty
                                    # print "total_qty>>>>>>>>>>>>>>>>>>", total_qty, total_credit, total_credit * (qty/total_qty)
                                    cost_component_each_item = (total_credit or 0.0) / total_qty                                
                                    new_std_price = (((amount_unit * product_avail[product.id])
                                        + (new_price * qty)) / (product_avail[product.id] + qty)) + cost_component_each_item
                                    
                                    print "cost component ", cost_component_each_item
                                    print "amount_unit", amount_unit
                                    print "product_avail", product_avail[product.id]
                                    print "new_price", new_price
                                    print "qty", qty           
                                    print "new_std_price", new_std_price                     
                                                                
                                    
                                    #print "new_std_price", new_std_price    
                                                                                       
                                
                                
                                    
                            # Write the field according to price type field
                            #product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price})
                            
                            product_obj.write(cr, uid, [product.id], {
                                                                      'standard_price'  : new_std_price,
                                                                      'list_price'      : new_std_price,
                                                                      'base_cost'       : new_std_price,                                                                                                                                                                                                                                                                                              
                                                                      })
    
                            # Record the values that were chosen in the wizard, so they can be
                            # used for inventory valuation if real-time valuation is enabled.
                            move_obj.write(cr, uid, [move.id],
                                    {'price_unit': product_price,
                                     'price_currency_id': product_currency})
                    
                    # Internal Update Cost Price
                    elif (pick.type == 'internal') and (move.product_id.cost_method == 'average') and (pick.internal_move_type == 'overseas'):                                                       
                        print "masuk internal"
                        product = product_obj.browse(cr, uid, move.product_id.id)
                        #move_currency_id = move.company_id.currency_id.id
                        #context['currency_id'] = move_currency_id
                        qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)                        
                        total_qty = 0.0
                        #if pick.additional_cost_int == 'yes':
                        product = product_obj.browse(cr, uid, move.product_id.id)
                        amount_unit = product.price_get('standard_price', context=context)[product.id]
                        product_avail[product.id] = product.qty_available                        
                        print "pritn foc prod", product.foc
                        if product.foc == 'FOC':
                            qty = 0                                                                        
                        
                        ####Change
                        #cr.execute("select sum(product_qty) from stock_move where picking_id = %s" % pick.id)
                        #total_qty = cr.fetchone()[0]
                        if qty > 0:
                            for move in pick.move_lines:
                                partial_data = partial_datas.get('move%s' % (move.id), {})
                                product_qty = partial_data.get('product_qty', 0.0)                    
                                product_price = partial_data.get('product_price', 0.0)
                                product_id = partial_data.get('product_id', False)
                                prod = product_obj.browse(cr, uid, product_id)
                                print prod.foc                        
                                if prod.foc == 'Regular':                                                                                                    
                                    total_qty += product_qty
                                                        
                            result_jkt_cost = 0.0    
                            real_price = 0.0                    
                            cost_component_each_item = total_credit / (total_qty or 0.0)                    
                            result_jkt_cost = product.base_cost + cost_component_each_item
                            if product.real_price == 0:
                                real_price = real_price = result_jkt_cost + (result_jkt_cost * (product.margin/ 100))
                            else:
                                real_price = product.real_price
                            print "jkt_cost ", product.jkt_cost,product.base_cost, cost_component_each_item                                         
                            
                            #=======================================================
                            # print "amount_unit INTERNAL", amount_unit
                            # print "product_avail INTERNAL", product_avail
                            # #print "new_price INTERNAL", new_price
                            # print "qty INTERNAL", qty
                            # print "cost_component_each_item INTERNAL", cost_component_each_item
                            # 
                            # 
                            # 
                            # print "new_std_price", new_std_price
                            #=======================================================
                            
                            #product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price})
                            ##EDIT TO
                            product_obj.write(cr, uid, [product.id], {
                                                                      'jkt_cost'        : result_jkt_cost,                                                                                                                                
                                                                      'real_price'      : real_price,
                                                                      'standard_price'  : result_jkt_cost,                                                              
                                                                      })

            for move in too_few:
                product_qty = move_product_qty[move.id]
                if not new_picking:
                    new_picking_name = pick.name
                    self.write(cr, uid, [pick.id],
                               {'name': sequence_obj.get(cr, uid,
                                            'stock.picking.%s' % (pick.type)),
                               })
                    new_picking = self.copy(cr, uid, pick.id,
                            {
                                'name': new_picking_name,
                                'move_lines' : [],
                                'state':'draft',
                            })
                if product_qty != 0:
                    defaults = {
                            'product_qty' : product_qty,
                            'product_uos_qty': product_qty, #TODO: put correct uos_qty
                            'picking_id' : new_picking,
                            'state': 'assigned',
                            'move_dest_id': False,
                            'price_unit': move.price_unit,
                            'product_uom': product_uoms[move.id]
                    }
                    prodlot_id = prodlot_ids[move.id]
                    if prodlot_id:
                        defaults.update(prodlot_id=prodlot_id)
                    move_obj.copy(cr, uid, move.id, defaults)
                move_obj.write(cr, uid, [move.id],
                        {
                            'product_qty': move.product_qty - partial_qty[move.id],
                            'product_uos_qty': move.product_qty - partial_qty[move.id], #TODO: put correct uos_qty
                            'prodlot_id': False,
                            'tracking_id': False,                            
                        })

            if new_picking:
                move_obj.write(cr, uid, [c.id for c in complete], {'picking_id': new_picking})
            for move in complete:
                defaults = {'product_uom': product_uoms[move.id], 'product_qty': move_product_qty[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move_obj.write(cr, uid, [move.id], defaults)
            for move in too_many:
                product_qty = move_product_qty[move.id]
                defaults = {
                    'product_qty' : product_qty,
                    'product_uos_qty': product_qty, #TODO: put correct uos_qty
                    'product_uom': product_uoms[move.id],                    
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                move_obj.write(cr, uid, [move.id], defaults)

            # At first we confirm the new picking (if necessary)
            if new_picking:
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
                # Then we finish the good picking
                self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
                self.action_move(cr, uid, [new_picking], context=context)
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_done', cr)
                wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
                delivered_pack_id = new_picking
                back_order_name = self.browse(cr, uid, delivered_pack_id, context=context).name
                self.message_post(cr, uid, ids, body=_("Back order <em>%s</em> has been <b>created</b>.") % (back_order_name), context=context)
            else:
                self.action_move(cr, uid, [pick.id], context=context)
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_done', cr)
                delivered_pack_id = pick.id

            delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
            res[pick.id] = {'delivered_picking': delivered_pack.id or False}

        return res
    
    
#     #Send mail sans queue
#     def dsp_send_email(self, cr, uid, pick_id, context=None):
        #=======================================================================
        # email_template_obj = self.pool.get('email.template')
        # template_ids = email_template_obj.search(cr, uid, [('model_id.model', '=','stock.picking.out')], context=context)
        # body_html = self.pool.get('email.template').browse(cr, uid, template_ids[0],context=context).body_html                
        # current_email = self.pool.get('res.users').browse(cr, uid, uid, context=context).email
        # name = self.browse(cr, uid, pick_id, context=context).name        
        # origin = self.browse(cr, uid, pick_id, context=context).origin
        # type = self.browse(cr, uid, pick_id, context=context).type
        # file_confirmed = self.browse(cr, uid, pick_id, context=context).file_confirmed
        # 
        # if template_ids:
        #     values = email_template_obj.generate_email(cr, uid, template_ids[0], pick_id , context=context)
        #     values['subject'] = 'Delivery Order ' + str(name) + str(type)
        #     values['email_from'] = current_email
        #     values['email_to'] = 'samuel.alfius@gmail.com'
        #     values['body_html'] = str(name) + '---' + str(origin)
        #     values['body'] = 'body'
        #     values['res_id'] = False
        #     values['attachment'] = file_confirmed
        #     mail_mail_obj = self.pool.get('mail.mail')
        #     msg_id = mail_mail_obj.create(cr, uid, values, context=context)            
        #     if msg_id:
        #           mail_mail_obj.send(cr, uid, [msg_id], context=context) 
        # return True
        #=======================================================================
        
    def dsp_send_email(self, cr, uid, pick_id, res_id, context=None):
        email_template_obj = self.pool.get('email.template')
        template_ids = email_template_obj.search(cr, uid, [('model_id.model', '=','stock.picking.out')], context=context) 
        if template_ids:
            email_template_obj.send_mail(cr, uid, template_ids[0], res_id, force_send=True, context=context)
        return True
 
    _defaults = {
            'additional_cost'       : 'no',
            'additional_cost_int'   : 'no',
            'internal_move_type'    : 'regular',
            'move_type'             : 'one',
                 }

stock_picking()

class stock_picking_out(osv.osv):
    #_name = "stock.picking.in"
    _inherit = "stock.picking.out"    
    _columns = {            
            'person_name'           : fields.char('Person Name', size=128),
            'date_confirmed'        : fields.date('Input Date'),
            'file_confirmed'        : fields.binary('Input File'),
            'person_name_ex'        : fields.char('Person Name', size=128),
            'date_confirmed_ex'     : fields.date('Input Date'),
            'file_confirmed_ex'     : fields.binary('Input File'),
            'notes_ex'              : fields.text('Notes'),
            'sale_ref'              : fields.many2one('sale.order', 'Source Document'),
            'consignment'           : fields.char('Sale Type'),
            'sale_warehouse'        : fields.char('Warehouse'),
            'sales_person'          : fields.char('Sales Person'),
                }
    
    _defaults = {            
            'move_type'             : 'one',
            'sale_ref'              : [0],
                 }

stock_picking_out()                
    

class stock_picking_in(osv.osv):
    #_name = "stock.picking.in"
    _inherit = "stock.picking.in"
    
    _columns = {
            'journal_id'            : fields.many2one('account.journal', 'Bank/ Cash'),
            'cost_component_line'   : fields.one2many('cost.component', 'picking_id', 'Contains'),
            'additional_cost'       : fields.selection([('no', 'Non Cost Component'), ('yes', 'With Cost Component')], 'Cost Component', readonly=False),
            'person_name'           : fields.char('Person Name', size=128),
            'date_confirmed'        : fields.date('Input Date'),
            'file_confirmed'        : fields.binary('Purchase Order File'),
            'consignment'           : fields.char('Sale Type'),         
            'sales_person'          : fields.char('Sales Person'),   
                }
    
    _defaults = {
            'additional_cost' : 'no',
            'move_type'       : 'one',
                 }

stock_picking_in()

class cost_component(osv.osv):
    _name = 'cost.component'
    
    _columns = {
            'picking_id'    : fields.many2one('stock.picking.in', 'Picking ID', required=True),
            'name'          : fields.char('Description', size=128, required=True),
            'quantity'      : fields.float('Quantity', required=True),
            'account_id'    : fields.many2one('account.account', 'Account', required=True),
            'amount'        : fields.float('Amount', required=True),
            'journal_id'    : fields.many2one('account.journal', 'Bank/ Cash'),
                }
    
    _defaults = {
            'quantity'  : 1,
            'amount'    : 0.0,
                }

    
cost_component()

class stock_move(osv.osv):    
    _inherit = "stock.move"
    
    #===========================================================================
    # def _compute_net_total(self, cr, uid, ids):        
    #     for line in self.browse(cr, uid, ids):
    #         price = line.price_unit                        
    #     return price
    #===========================================================================
    
    def _compute_sub_total(self, cr, uid, ids, price_unit, qty):                
        price = price_unit * qty                        
        return price
        
    _columns = {
            #'price_unit': fields.float('Unit Price', store=True, digits_compute= dp.get_precision('Product Price'), help="Technical field used to record the product cost set by the user during a picking confirmation (when average price costing method is used)"),
            'net_total'    : fields.float('Unit Price', digits_compute= dp.get_precision('Product Price')),
            'price_unit2': fields.float('Unit Price', digits_compute= dp.get_precision('Product Price')),            
            'price_unit_view': fields.related('price_unit', type='float', string='Unit Price', readonly=True),
                }    
        
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False,
                            loc_dest_id=False, partner_id=False):
        """ On change of product id, if finds UoM, UoS, quantity and UoS quantity.
        @param prod_id: Changed Product id
        @param loc_id: Source location id
        @param loc_dest_id: Destination location id
        @param partner_id: Address id of partner
        @return: Dictionary of values
        """
        if not prod_id:
            return {}
        user = self.pool.get('res.users').browse(cr, uid, uid)
        lang = user and user.lang or False
        if partner_id:
            addr_rec = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if addr_rec:
                lang = addr_rec and addr_rec.lang or False
        ctx = {'lang': lang}

        product = self.pool.get('product.product').browse(cr, uid, [prod_id], context=ctx)[0]
        uos_id  = product.uos_id and product.uos_id.id or False
        result = {
            'product_uom': product.uom_id.id,
            'product_uos': uos_id,
            'product_qty': 1.00,
            'product_uos_qty' : self.pool.get('stock.move').onchange_quantity(cr, uid, ids, prod_id, 1.00, product.uom_id.id, uos_id)['value']['product_uos_qty'],
            'prodlot_id' : False,
            'price_unit' : product.real_price,
            'price_unit_view' : product.real_price,            
        }
        if not ids:
            result['name'] = product.partner_ref
        if loc_id:
            result['location_id'] = loc_id
        if loc_dest_id:
            result['location_dest_id'] = loc_dest_id
        return {'value': result}            
    
    def action_done(self, cr, uid, ids, context=None):
        """ Makes the move done and if all moves are done, it will finish the picking.
        @return:
        """        
        picking_ids = []
        move_ids = []
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}

        todo = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state=="draft":
                todo.append(move.id)
        if todo:
            self.action_confirm(cr, uid, todo, context=context)
            todo = []

        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ['done','cancel']:
                continue
            move_ids.append(move.id)

            if move.picking_id:
                picking_ids.append(move.picking_id.id)
            if move.move_dest_id.id and (move.state != 'done'):
                # Downstream move should only be triggered if this move is the last pending upstream move
                other_upstream_move_ids = self.search(cr, uid, [('id','!=',move.id),('state','not in',['done','cancel']),
                                            ('move_dest_id','=',move.move_dest_id.id)], context=context)
                if not other_upstream_move_ids:
                    self.write(cr, uid, [move.id], {'move_history_ids': [(4, move.move_dest_id.id)]})
                    if move.move_dest_id.state in ('waiting', 'confirmed'):
                        self.force_assign(cr, uid, [move.move_dest_id.id], context=context)
                        if move.move_dest_id.picking_id:
                            wf_service.trg_write(uid, 'stock.picking', move.move_dest_id.picking_id.id, cr)
                        if move.move_dest_id.auto_validate:
                            self.action_done(cr, uid, [move.move_dest_id.id], context=context)

            #self._create_product_valuation_moves(cr, uid, move, context=context)
            if move.state not in ('confirmed','done','assigned'):
                todo.append(move.id)

        if todo:
            self.action_confirm(cr, uid, todo, context=context)

        self.write(cr, uid, move_ids, {'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        for id in move_ids:
             wf_service.trg_trigger(uid, 'stock.move', id, cr)

        for pick_id in picking_ids:
            wf_service.trg_write(uid, 'stock.picking', pick_id, cr)

        return True
    
stock_move()    

class product_product(osv.osv):
    _inherit = 'product.product'
        
    def get_product_available(self, cr, uid, ids, context=None):
        """ Finds whether product is available or not in particular warehouse.
        @return: Dictionary of values
        """        
        
        if context is None:
            context = {}
        
        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')
        shop_obj = self.pool.get('sale.shop')
        
        states = context.get('states',[])
        what = context.get('what',())
        if not ids:
            ids = self.search(cr, uid, [])
        res = {}.fromkeys(ids, 0.0)
        if not ids:
            return res

        if context.get('shop', False):
            warehouse_id = shop_obj.read(cr, uid, int(context['shop']), ['warehouse_id'])['warehouse_id'][0]
            if warehouse_id:
                context['warehouse'] = warehouse_id

        if context.get('warehouse', False):
            lot_id = warehouse_obj.read(cr, uid, int(context['warehouse']), ['lot_stock_id'])['lot_stock_id'][0]
            if lot_id:
                context['location'] = lot_id

        if context.get('location', False):
            if type(context['location']) == type(1):
                location_ids = [context['location']]
            elif type(context['location']) in (type(''), type(u'')):
                location_ids = location_obj.search(cr, uid, [('name','ilike',context['location'])], context=context)
            else:
                location_ids = context['location']
        else:
            location_ids = []
            wids = warehouse_obj.search(cr, uid, [], context=context)
            if not wids:
                return res
            for w in warehouse_obj.browse(cr, uid, wids, context=context):
                location_ids.append(w.lot_stock_id.id)

        # build the list of ids of children of the location given by id
        if context.get('compute_child',True):
            child_location_ids = location_obj.search(cr, uid, [('location_id', 'child_of', location_ids)])
            location_ids = child_location_ids or location_ids
        
        # this will be a dictionary of the product UoM by product id
        product2uom = {}
        uom_ids = []
        for product in self.read(cr, uid, ids, ['uom_id'], context=context):
            product2uom[product['id']] = product['uom_id'][0]
            uom_ids.append(product['uom_id'][0])
        # this will be a dictionary of the UoM resources we need for conversion purposes, by UoM id
        uoms_o = {}
        for uom in self.pool.get('product.uom').browse(cr, uid, uom_ids, context=context):
            uoms_o[uom.id] = uom

        results = []
        results2 = []

        from_date = context.get('from_date',False)
        to_date = context.get('to_date',False)
        date_str = False
        date_values = False
        where = [tuple(location_ids),tuple(location_ids),tuple(ids),tuple(states)]
        if from_date and to_date:
            date_str = "date>=%s and date<=%s"
            where.append(tuple([from_date]))
            where.append(tuple([to_date]))
        elif from_date:
            date_str = "date>=%s"
            date_values = [from_date]
        elif to_date:
            date_str = "date<=%s"
            date_values = [to_date]
        if date_values:
            where.append(tuple(date_values))

        prodlot_id = context.get('prodlot_id', False)
        prodlot_clause = ''
        if prodlot_id:
            prodlot_clause = ' and prodlot_id = %s '
            where += [prodlot_id]

        # TODO: perhaps merge in one query.
        if 'in' in what:
            # all moves from a location out of the set to a location in the set
            cr.execute(
                'select sum(product_qty), product_id, product_uom '\
                'from stock_move '\
                'where location_id NOT IN %s '\
                'and location_dest_id IN %s '\
                'and product_id IN %s '\
                'and state IN %s ' + (date_str and 'and '+date_str+' ' or '') +' '\
                + prodlot_clause + 
                'group by product_id,product_uom',tuple(where))
            results = cr.fetchall()
        if 'out' in what:
            # all moves from a location in the set to a location out of the set
            cr.execute(
                'select sum(product_qty), product_id, product_uom '\
                'from stock_move '\
                'where location_id IN %s '\
                'and location_dest_id NOT IN %s '\
                'and product_id  IN %s '\
                'and state in %s ' + (date_str and 'and '+date_str+' ' or '') + ' '\
                + prodlot_clause + 
                'group by product_id,product_uom',tuple(where))
            results2 = cr.fetchall()
            
        # Get the missing UoM resources
        uom_obj = self.pool.get('product.uom')
        uoms = map(lambda x: x[2], results) + map(lambda x: x[2], results2)
        if context.get('uom', False):
            uoms += [context['uom']]
        uoms = filter(lambda x: x not in uoms_o.keys(), uoms)
        if uoms:
            uoms = uom_obj.browse(cr, uid, list(set(uoms)), context=context)
            for o in uoms:
                uoms_o[o.id] = o
                
        #TOCHECK: before change uom of product, stock move line are in old uom.
        context.update({'raise-exception': False})
        # Count the incoming quantities
        for amount, prod_id, prod_uom in results:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                     uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
            res[prod_id] += amount
        # Count the outgoing quantities
        for amount, prod_id, prod_uom in results2:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                    uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
            res[prod_id] -= amount
        return res
    
    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
        """ Finds the incoming and outgoing quantity of product.
        @return: Dictionary of values
        """
        if not field_names:
            field_names = []
        if context is None:
            context = {}
        res = {}
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0.0)
        for f in field_names:
            c = context.copy()
            if f == 'qty_available':
                c.update({ 'states': ('done',), 'what': ('in', 'out') })
            if f == 'virtual_available':
                c.update({ 'states': ('confirmed','waiting','assigned','done'), 'what': ('in', 'out') })
            if f == 'incoming_qty':
                c.update({ 'states': ('confirmed','waiting','assigned'), 'what': ('in',) })
            if f == 'outgoing_qty':
                c.update({ 'states': ('confirmed','waiting','assigned'), 'what': ('out',) })
            stock = self.get_product_available(cr, uid, ids, context=c)            
            for id in ids:
                if (f == 'qty_available' or f == 'virtual_available'):
                    prod_obj = self.browse(cr, uid, id, context=context)
                    qty_on_hand = stock.get(id, 0.0) - prod_obj.qty_adjusted_out + prod_obj.qty_adjusted_in                    
                    res[id][f] = qty_on_hand                    
                else:                                
                    res[id][f] = stock.get(id, 0.0)
                print res
        return res
    
    _columns = {
                'qty_available': fields.function(_product_available, multi='qty_available',
                    type='float',  digits_compute=dp.get_precision('Product Unit of Measure'),
                    string='Quantity On Hand',
                    help="Current quantity of products.\n"
                    "In a context with a single Stock Location, this includes "
                    "goods stored at this Location, or any of its children.\n"
                    "In a context with a single Warehouse, this includes "
                    "goods stored in the Stock Location of this Warehouse, or any "
                    "of its children.\n"
                    "In a context with a single Shop, this includes goods "
                    "stored in the Stock Location of the Warehouse of this Shop, "
                    "or any of its children.\n"
                    "Otherwise, this includes goods stored in any Stock Location "
                    "with 'internal' type."),
                'virtual_available': fields.function(_product_available, multi='qty_available',
                    type='float',  digits_compute=dp.get_precision('Product Unit of Measure'),
                    string='Forecasted Quantity',
                    help="Forecast quantity (computed as Quantity On Hand "
                         "- Outgoing + Incoming)\n"
                         "In a context with a single Stock Location, this includes "
                         "goods stored in this location, or any of its children.\n"
                         "In a context with a single Warehouse, this includes "
                         "goods stored in the Stock Location of this Warehouse, or any "
                         "of its children.\n"
                         "In a context with a single Shop, this includes goods "
                         "stored in the Stock Location of the Warehouse of this Shop, "
                         "or any of its children.\n"
                         "Otherwise, this includes goods stored in any Stock Location "
                         "with 'internal' type."),
                }
    
    
product_product()

class stock_adjustment(osv.osv):
    _name = 'stock.adjustment'   
    
    def _default_location_source(self, cr, uid, context=None):
        """ Gets default address of partner for source location
        @return: Address id or False
        """
        mod_obj = self.pool.get('ir.model.data')
        picking_type = context.get('picking_type')
        location_id = False

        if context is None:
            context = {}
        if context.get('move_line', []):
            try:
                location_id = context['move_line'][0][2]['location_id']
            except:
                pass
        elif context.get('address_in_id', False):
            part_obj_add = self.pool.get('res.partner').browse(cr, uid, context['address_in_id'], context=context)
            if part_obj_add:
                location_id = part_obj_add.property_stock_supplier.id
        else:
            location_xml_id = False
            if picking_type == 'in':
                location_xml_id = 'stock_location_suppliers'
            elif picking_type in ('out', 'internal'):
                location_xml_id = 'stock_location_stock'
            if location_xml_id:
                try:
                    location_model, location_id = mod_obj.get_object_reference(cr, uid, 'stock', location_xml_id)
                    with tools.mute_logger('openerp.osv.orm'):
                        self.pool.get('stock.location').check_access_rule(cr, uid, [location_id], 'read', context=context)
                except (orm.except_orm, ValueError):
                    location_id = False

        return location_id
     
    _columns = {
            'product_id'            : fields.many2one('product.product', 'Product', required=True),
            'date'                  : fields.date('Adjusted Date'),
            'account_id'            : fields.many2one('account.account', 'Account', required=True),                    
            'journal_id'            : fields.many2one('account.journal', 'Journal', required=True),
            'invoice_id'            : fields.many2one('account.invoice', 'Invoice Ref', required=True, domain=[('type','=','out_invoice')]),
            'qty_on_hand'           : fields.float('Qty On Hand' , digits_compute= dp.get_precision('Product Unit Of Measure')),            
            'price'                 : fields.float('Cost Price', digits_compute= dp.get_precision('Product Price')),
            'product_id_adj'        : fields.many2one('product.product', 'Product to Adjust'),
            'qty_on_hand_adj'       : fields.float('Qty On Hand', digits_compute= dp.get_precision('Product Unit Of Measure')),                                
            'qty_adj'               : fields.float('Qty to Adjust', digits_compute= dp.get_precision('Product Unit Of Measure')),
            'price_adj'             : fields.float('Price to Adjust', digits_compute= dp.get_precision('Product Price')),
            'location_id'           : fields.many2one('stock.location', 'Source Location', required=True),
            'location_dest_id'      : fields.many2one('stock.location', 'Destination Location', required=True),
            'location_id_adj'       : fields.many2one('stock.location', 'Source Location', required=True),
            'location_dest_id_adj'  : fields.many2one('stock.location', 'Destination Location', required=True),
            'state'                 : fields.selection([('draft', 'Draft'),('done', 'Done'),('cancel', 'Cancel')], 'Status', readonly=True),
            'qty'                   : fields.float('Qty to Return', digits_compute= dp.get_precision('Product Unit Of Measure')),
            'person_name'           : fields.char('Person Name', size=128, required=True),
            'date_confirmed'        : fields.date('Input Date', required=True),
            'file_confirmed'        : fields.binary('Confirmation File', required=True),
        }      
    
    _defaults = {
                 'state' : 'draft',
                 'account_id' : 421,
                 'journal_id' : 1,
                 'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
                 'location_id' : 5, #inventory loss
                 'location_dest_id' : 12,
                 'location_id_adj' : 12,
                 'location_dest_id_adj' : 9 #customers
                 }  
    
    def onchange_account_id(self, cr, uid, ids, account_id, context=None):
        if account_id:
            print account_id                                                                                                                                                    
        return True
    
    def onchange_journal_id(self, cr, uid, ids, journal_id, context=None):
        if journal_id:
            print journal_id                                                                                                                                                    
        return True
    
    def onchange_invoice_id(self, cr, uid, ids, invoice_id, product_id, context=None):        
        if not product_id:
            val = {
               'invoice_id' : False                
               }            
            raise osv.except_osv(_('Warning Confirmation !'), _('Please Choose Product First!"'))
            return {'value' : val}
        
        invoice_line_id = self.pool.get('account.invoice.line').search(cr, uid, [('invoice_id','=',invoice_id),('product_id','=',product_id)], context=context)
        invoice_line_obj = self.pool.get('account.invoice.line').browse(cr, uid, invoice_line_id)
                
        if invoice_line_obj:        
            qty = invoice_line_obj[0].quantity
            price = invoice_line_obj[0].jkt_cost        
        else:
            qty = 0.0
            price = 0.0        
        
        val = {
               'qty' : qty,
               'qty_adj' : qty,
               'price' : price
               }
                                                                                                                                      
        return {'value' : val}
    
    def onchange_product_id(self, cr, uid, ids, invoice_id, product_id, context=None):
        qty = 0.0
        price = 0.0
        qty_avail = 0.0
                
        if product_id:   
            product_obj = self.pool.get('product.product').browse(cr, uid, product_id)                                    
            qty_avail = product_obj.qty_available
        else:
            qty_avail = 0
            
        if invoice_id:                
            invoice_line_id = self.pool.get('account.invoice.line').search(cr, uid, [('invoice_id','=',invoice_id),('product_id','=',product_id)], context=context)
            invoice_line_obj = self.pool.get('account.invoice.line').browse(cr, uid, invoice_line_id)                         
            
            if invoice_line_obj:        
                qty = invoice_line_obj[0].quantity
                price = invoice_line_obj[0].jkt_cost    
            else:
                qty = 0.0
                price = 0.0
        
        val = {
               'qty' : qty,
               'qty_adj' : qty,
               'price' : price,               
               'qty_on_hand' : qty_avail
               }
                                                                                                                                      
        return {'value' : val}
    
    def onchange_product_id_adj(self, cr, uid, ids, product_id, context=None):
        qty_avail = 0.0
        jkt_cost = 0.0
                                        
        if product_id:
            product_obj = self.pool.get('product.product').browse(cr, uid, product_id)
            qty_avail = product_obj.qty_available
            jkt_cost = product_obj.jkt_cost
        else:
            qty_avail = 0
            
        val = {               
               'qty_on_hand_adj' : qty_avail,
               'price_adj' : jkt_cost
               }
                                                                                                                                      
        return {'value' : val}
    
    def date_to_datetime(self, cr, uid, userdate, context=None):
        """ Convert date values expressed in user's timezone to
        server-side UTC timestamp, assuming a default arbitrary
        time of 12:00 AM - because a time is needed.
    
        :param str userdate: date string in in user time zone
        :return: UTC datetime string for server-side use
        """
        # TODO: move to fields.datetime in server after 7.0
        user_date = datetime.strptime(userdate, DEFAULT_SERVER_DATE_FORMAT)
        if context and context.get('tz'):
            tz_name = context['tz']
        else:
            tz_name = self.pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['tz'])['tz']
        if tz_name:
            utc = pytz.timezone('UTC')
            context_tz = pytz.timezone(tz_name)
            user_datetime = user_date + relativedelta(hours=12.0)
            local_timestamp = context_tz.localize(user_datetime, is_dst=False)
            user_datetime = local_timestamp.astimezone(utc)
            return user_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return user_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)


    def _prepare_order_line_move(self, cr, uid, stock_adj, context=None):
        invoice_line_id = self.pool.get('account.invoice.line').search(cr, uid, [('invoice_id','=',stock_adj.invoice_id.id),('product_id','=',stock_adj.product_id.id)], context=context)        
        invoice_line_obj = self.pool.get('account.invoice.line').browse(cr, uid, invoice_line_id)                                     
        if invoice_line_obj:        
            qty = invoice_line_obj[0].quantity
            price = invoice_line_obj[0].jkt_cost    
        else:
            qty = 0.0
            price = 0.0            
            
        return {
            'name': 'Stock Adjustment',
            'product_id': stock_adj.product_id.id,
            'product_qty': qty,
            'product_uom': stock_adj.product_id.uom_id.id,            
            'date': self.date_to_datetime(cr, uid, stock_adj.date, context),
            'date_expected': self.date_to_datetime(cr, uid, stock_adj.date, context),
            'location_id': stock_adj.location_id.id,
            'location_dest_id': stock_adj.location_dest_id.id,                                            
            'state': 'draft',
            'type':'in',            
            'price_unit': price
        }
        
    def _prepare_order_line_move_adj(self, cr, uid, stock_adj, context=None):
        invoice_line_id = self.pool.get('account.invoice.line').search(cr, uid, [('invoice_id','=',stock_adj.invoice_id.id),('product_id','=',stock_adj.product_id.id)], context=context)
        invoice_line_obj = self.pool.get('account.invoice.line').browse(cr, uid, invoice_line_id)                                     
        if invoice_line_obj:        
            qty_adj = invoice_line_obj[0].quantity            
        else:
            qty_adj = 0.0
                                
        product_obj_adj = self.pool.get('product.product').browse(cr, uid, stock_adj.product_id_adj.id)                                     
        if product_obj_adj:                        
            price_adj = product_obj_adj.jkt_cost    
        else:                
            price_adj = 0.0                    
            
        return {
            'name': 'Stock Adjustment',
            'product_id': stock_adj.product_id_adj.id,
            'product_qty': qty_adj,
            'product_uom': stock_adj.product_id_adj.uom_id.id,            
            'date': self.date_to_datetime(cr, uid, stock_adj.date, context),
            'date_expected': self.date_to_datetime(cr, uid, stock_adj.date, context),
            'location_id': stock_adj.location_id_adj.id,
            'location_dest_id': stock_adj.location_dest_id_adj.id,                                            
            'state': 'draft',
            'type':'out',            
            'price_unit': price_adj
        }
        
    def stock_adjustment_confirm(self, cr, uid, ids, context=None):
        todo_moves = []
        stock_move = self.pool.get('stock.move')                
        for stock_adj in self.browse(cr, uid, ids, context=context):
            product_obj = self.pool.get('product.product').browse(cr, uid, stock_adj.product_id.id)
            account_valuation = product_obj.categ_id.property_stock_valuation_account_id.id                               
            account_output = product_obj.categ_id.property_stock_account_output_categ.id            
            #===================================================================
            # Create Stock moves Product To Return
            #===================================================================
            move = stock_move.create(cr, uid, self._prepare_order_line_move(cr, uid, stock_adj, context=context))                        
            todo_moves.append(move)
            stock_move.action_confirm(cr, uid, todo_moves)
            stock_move.force_assign(cr, uid, todo_moves)
            stock_move.action_done(cr, uid, todo_moves)
            
            #===================================================================
            # Create stock moves Product to Adjust
            #===================================================================
            move = stock_move.create(cr, uid, self._prepare_order_line_move_adj(cr, uid, stock_adj, context=context))                        
            todo_moves.append(move)
            stock_move.action_confirm(cr, uid, todo_moves)
            stock_move.force_assign(cr, uid, todo_moves)
            stock_move.action_done(cr, uid, todo_moves)
                        
            invoice_line_id = self.pool.get('account.invoice.line').search(cr, uid, [('invoice_id','=',stock_adj.invoice_id.id),('product_id','=',stock_adj.product_id.id)], context=context)
            invoice_line_obj = self.pool.get('account.invoice.line').browse(cr, uid, invoice_line_id)                                     
            if invoice_line_obj:        
                qty = invoice_line_obj[0].quantity
                price = invoice_line_obj[0].jkt_cost    
            else:
                qty = 0.0
                price = 0.0                
                
            product_obj_adj = self.pool.get('product.product').browse(cr, uid, stock_adj.product_id_adj.id)                                     
            if product_obj_adj:                                    
                price_adj = product_obj_adj.jkt_cost    
            else:                
                price_adj = 0.0
            
            qty_adj = qty            
            
            #===================================================================
            # Posting Cost Of Goods Sold
            #===================================================================
            sequence_obj = self.pool.get('ir.sequence')
            move_pool = self.pool.get('account.move')
            move_line_pool = self.pool.get('account.move.line')
                                     
            seq = sequence_obj.get_id(cr, uid, stock_adj.journal_id.sequence_id.id)
     
            period_search = self.pool.get('account.period').search(cr, uid, [('date_start','<=',stock_adj.date),('date_stop','>=',stock_adj.date)])
            period_browse = self.pool.get('account.period').browse(cr, uid, period_search)                
            
            #===================================================================
            # Stock Journal Return
            #===================================================================        
            move = {
                    'name'          : seq or '/',
                    'journal_id'    : stock_adj.journal_id.id,                    
                    'date'          : stock_adj.date,                    
                    'period_id'     : period_browse[0].id,
                    'partner_id'    : False
                    }
          
            move_id = move_pool.create(cr, uid, move)            
            
            debit = (price * qty)
            move_line = {
                         'name'      : seq or '/',
                         'debit'     : debit,
                         'credit'    : 0.0,
                         'account_id': account_valuation, #inventory asset 
                         'move_id'   : move_id,
                         'journal_id': 9, #stock journal
                         'period_id' : period_browse[0].id,
                         'partner_id': False,
                         #'currency_id': 13,
                         #'amount_currency': company_currency <> current_currency and -bts.amount or 0.0,
                         'date'      : stock_adj.date,
                    }
            
            move_line_pool.create(cr, uid, move_line)
                  
            #print "total_credit", total_credit
            move_line = {
                         'name'      : seq or '/',
                         'debit'     : 0.0,
                         'credit'    : debit,
                         'account_id': account_output, #cost of goods sold
                         'move_id'   : move_id,
                         'journal_id': 9, #stock journal
                         'period_id' : period_browse[0].id,
                         'partner_id': False,
                         #'currency_id': 13,
                         #'amount_currency': company_currency <> current_currency and -bts.amount or 0.0,
                         'date'      : stock_adj.date,
                    }
            move_line_pool.create(cr, uid, move_line)
              
            move_pool.post(cr, uid, [move_id], context={})
            
            #===================================================================
            # Stock Journal Adjust
            #===================================================================
            move = {
                    'name'          : seq or '/',
                    'journal_id'    : stock_adj.journal_id.id,                    
                    'date'          : stock_adj.date,                    
                    'period_id'     : period_browse[0].id,
                    'partner_id'    : False
                    }
          
            move_id = move_pool.create(cr, uid, move)
                                              
            debit = (price * qty)
            debit_adj = (price_adj * qty_adj)
            
            gain_loss = 0.0
            if debit > debit_adj:
                gain_loss = debit-debit_adj    
                                        
                move_line = {
                             'name'      : seq or '/',
                             'debit'     : debit,
                             'credit'    : 0.0,
                             'account_id': account_output,  
                             'move_id'   : move_id,
                             'journal_id': 9, #stock journal
                             'period_id' : period_browse[0].id,
                             'partner_id': False,
                             #'currency_id': 13,
                             #'amount_currency': company_currency <> current_currency and -bts.amount or 0.0,
                             'date'      : stock_adj.date,
                        }                
                move_line_pool.create(cr, uid, move_line)                      
                
                move_line = {
                             'name'      : seq or '/',
                             'debit'     : 0.0,
                             'credit'    : debit_adj,
                             'account_id': account_valuation,
                             'move_id'   : move_id,
                             'journal_id': 9, #stock journal
                             'period_id' : period_browse[0].id,
                             'partner_id': False,
                             #'currency_id': 13,
                             #'amount_currency': company_currency <> current_currency and -bts.amount or 0.0,
                             'date'      : stock_adj.date,
                        }
                move_line_pool.create(cr, uid, move_line)
                
                move_line = {
                             'name'      : seq or '/',
                             'debit'     : 0.0,
                             'credit'    : gain_loss,
                             'account_id': 461, #expense cost for products
                             'move_id'   : move_id,
                             'journal_id': 9, #expense journal
                             'period_id' : period_browse[0].id,
                             'partner_id': False,
                             #'currency_id': 13,
                             #'amount_currency': company_currency <> current_currency and -bts.amount or 0.0,
                             'date'      : stock_adj.date,
                        }
                move_line_pool.create(cr, uid, move_line)
                  
                move_pool.post(cr, uid, [move_id], context={})
            
            elif debit < debit_adj:
                gain_loss = debit_adj-debit    
                                        
                move_line = {
                             'name'      : seq or '/',
                             'debit'     : debit,
                             'credit'    : 0.0,
                             'account_id': account_output, 
                             'move_id'   : move_id,
                             'journal_id': 9, #stock journal
                             'period_id' : period_browse[0].id,
                             'partner_id': False,
                             #'currency_id': 13,
                             #'amount_currency': company_currency <> current_currency and -bts.amount or 0.0,
                             'date'      : stock_adj.date,
                        }                
                move_line_pool.create(cr, uid, move_line)
                
                move_line = {
                             'name'      : seq or '/',
                             'debit'     : gain_loss,
                             'credit'    : 0.0,
                             'account_id': 461, #expense cost for products
                             'move_id'   : move_id,
                             'journal_id': 9, #expense journal
                             'period_id' : period_browse[0].id,
                             'partner_id': False,
                             #'currency_id': 13,
                             #'amount_currency': company_currency <> current_currency and -bts.amount or 0.0,
                             'date'      : stock_adj.date,
                        }
                move_line_pool.create(cr, uid, move_line)                      
                
                move_line = {
                             'name'      : seq or '/',
                             'debit'     : 0.0,
                             'credit'    : debit_adj,
                             'account_id': account_valuation,
                             'move_id'   : move_id,
                             'journal_id': 9, #stock journal
                             'period_id' : period_browse[0].id,
                             'partner_id': False,
                             #'currency_id': 13,
                             #'amount_currency': company_currency <> current_currency and -bts.amount or 0.0,
                             'date'      : stock_adj.date,
                        }
                move_line_pool.create(cr, uid, move_line)                                
                  
                move_pool.post(cr, uid, [move_id], context={})
                            
        self.write(cr, uid, ids, {'state':'done'})                            
        return True                        
    
    def stock_adjustment_cancel(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state':'cancel'})
        return True        
        
stock_adjustment()