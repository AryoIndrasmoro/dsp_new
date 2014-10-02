from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
from operator import itemgetter
from itertools import groupby

from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
import logging


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
                                    cost_component_each_item = total_credit / (total_qty or 0.0)                                
                                    new_std_price = ((amount_unit * product_avail[product.id])\
                                        + (new_price * qty) + cost_component_each_item) / (product_avail[product.id] + qty)
                                    
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
                        product = product_obj.browse(cr, uid, move.product_id.id)
                        #move_currency_id = move.company_id.currency_id.id
                        #context['currency_id'] = move_currency_id
                        qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)                        
                        total_qty = 0.0
                        #if pick.additional_cost_int == 'yes':
                        product = product_obj.browse(cr, uid, move.product_id.id)
                        amount_unit = product.price_get('standard_price', context=context)[product.id]
                        product_avail[product.id] = product.qty_available                        
                        print product.foc
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
                                                                      'standard_price'  : real_price,                                                              
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

stock_move()    