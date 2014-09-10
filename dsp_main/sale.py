from openerp.osv import fields,osv
import pdb
import pprint
import time
from datetime import datetime

class sale_order(osv.osv):
    _inherit = "sale.order"
    _description = "Sales Order Inherit DSP"
    
    def action_confirm_quotation(self, cr, uid, ids, context=None):        
        return self.write(cr, uid, ids, {'state': 'quotation_confirm'})        
    
    def _prepare_order_picking(self, cr, uid, order, context=None):        
        pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
        current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        sale_type = order.sale_type
        
        print "aaaaaaaaaaaaaaaaaaaaa" , current_user.name
        
        if sale_type == 'Consignment':
            sale_type = 'Consignment'
        elif sale_type == 'Outlet (Direct Selling)':
            sale_type = 'Direct Selling'
        else:
            sale_type = 'Promo'            
        
        return {
            'name': pick_name,
            'origin': order.name,
            'date': self.date_to_datetime(cr, uid, order.date_order, context),
            'type': 'out',
            'state': 'auto',
            'move_type': order.picking_policy,
            'sale_id': order.id,
            'partner_id': order.partner_shipping_id.id,
            'note': order.note,
            'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
            'company_id': order.company_id.id,
            'sale_warehouse' : order.shop_id.name,
            'consignment' : sale_type,
            'sales_person' : current_user.name,   
            'price_unit'    : 100,         
        }
        
    _columns ={
               'partner_id'         : fields.many2one('res.partner', 'Outlet/Customer', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, change_default=True, select=True, track_visibility='always'),
               'sale_type'          : fields.selection([('Promo', 'Promo'), ('Consignment', 'Consignment'),('Outlet (Direct Selling)','Outlet (Direct Selling)') ], 'Sale Type'),
               'person_name'        : fields.char('Person Name', size=128),
               'date_confirmed'     : fields.date('Input Date'),
               'file_confirmed'     : fields.binary('Quotation File'),
               'person_name_order'    : fields.char('Person Name', size=128),
               'date_confirmed_order' : fields.date('Input Date'),
               'file_confirmed_order' : fields.binary('Sales Order File'),
               'dsp_price_list_id': fields.selection([('real', 'Real Price'), ('outlet', 'Outlet Price')], 'DSP Price List'),
               'state': fields.selection([
                    ('draft', 'Draft Quotation'),
                    ('sent', 'Quotation Sent'),
                    ('cancel', 'Cancelled'),
                    ('waiting_date', 'Waiting Schedule'),
                    ('quotation_confirm', 'Quotation Confirmed'),                    
                    ('progress', 'Sales Order'),
                    ('order_confirm', 'Order Confirmed'),
                    ('manual', 'Sale to Invoice'),
                    ('invoice_except', 'Invoice Exception'),
                    ('done', 'Done'),
                    ], 'Status', readonly=True, track_visibility='onchange',
                    help="Gives the status of the quotation or sales order. \nThe exception status is automatically set when a cancel operation occurs in the processing of a document linked to the sales order. \nThe 'Waiting Schedule' status is set when the invoice is confirmed but waiting for the scheduler to run on the order date.", select=True),    
            }
    
    def _prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        location_id = order.shop_id.warehouse_id.lot_stock_id.id
        output_id = order.shop_id.warehouse_id.lot_output_id.id
        return {
            'name': line.name,
            'picking_id': picking_id,
            'product_id': line.product_id.id,
            'date': date_planned,
            'date_expected': date_planned,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id)\
                    or line.product_uom.id,
            'product_packaging': line.product_packaging.id,
            'partner_id': line.address_allotment_id.id or order.partner_shipping_id.id,
            'location_id': location_id,
            'location_dest_id': output_id,
            'sale_line_id': line.id,
            'tracking_id': False,
            'state': 'draft',
            #'state': 'waiting',
            'company_id': order.company_id.id,
            'price_unit': line.product_id.standard_price or 0.0
        }
        
    def create(self, cr, uid, vals, context=None):
        ##############ARYA Payment Alert###############
        
        fmt = '%Y-%m-%d'
        #date_today = lambda self,cr,uid,context={}: context.get('date', fields.date.context_today(self,cr,uid,context=context))
        date_today = time.strftime('%Y-%m-%d')
        res_partner = self.pool.get('res.partner')
        partner_id = vals['partner_id']
        partner_obj = self.pool.get('res.partner').browse(cr, uid, partner_id, context=None)        
        partner_bypass = partner_obj.bypass_order
        
        # check if there's still any open Invoice        
        invoice_search  = self.pool.get('account.invoice').search(cr, uid, [('partner_id','=',partner_id), ('state','=','open')], context=None)        
        # Get the list of open invoice                
        invoice_obj = self.pool.get('account.invoice').browse(cr, uid, invoice_search, context=None)
        # check due date of every single open invoice if there's any of them
        
        #=======================================================================
        # if invoice_obj:
        #     for inv in invoice_obj:                
        #         d1 = datetime.strptime(date_today, fmt)
        #         d2 = datetime.strptime(inv.date_due, fmt)                
        #         daysDiff = int((d1-d2).days) 
        #                          
        #         if daysDiff >= 0:  
        #             print daysDiff                  
        #             if partner_bypass == False:                                                
        #                 raise osv.except_osv(('Outstanding Payment!'),('You cannot save if outlet have outstanding payment!'))
        #             elif partner_bypass == True:
        #                 res_partner.write(cr, uid, partner_id, {'bypass_order' : False})
        #         else:
        #             print "out"
        #=======================================================================
        
        if invoice_obj:                
            if partner_bypass == False:                                                
                raise osv.except_osv(('Outstanding Payment!'),('You cannot save if outlet have outstanding payment!'))
            elif partner_bypass == True:
                res_partner.write(cr, uid, partner_id, {'bypass_order' : False})
        else:
            print "out"
                                                                                                                                                                
        ###############################################
        if vals.get('name','/')=='/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/'
        return super(sale_order, self).create(cr, uid, vals, context=context)
    
#===============================================================================
#     def create(self, cr, uid, vals, context=None):
#         
#         if vals.get('sale_type')=='Promo':
#             for  n in range(len(vals.get('order_line'))):
#                 vals['order_line'][n][2]['discount']=100
#                     
#         if vals.get('name','/')=='/':
#             vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/'
#         return super(sale_order, self).create(cr, uid, vals, context=context)    
# 
#     def write(self, cr, uid, ids, vals, context=None):
# 
#         for sale in self.browse(cr, uid, ids, context=context):
#             if sale.sale_type =='Promo':
#                 for  n in range(len(vals.get('order_line'))):
#                     if bool(vals['order_line'][n][2]):
#                         vals['order_line'][n][2]['discount']=100
#             
#         return super(sale_order, self).write(cr, uid, ids, vals, context=context)                                
#===============================================================================    
    
    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        if not part:
            return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False,  'payment_term': False, 'fiscal_position': False}}

        part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
        addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        payment_term = part.property_payment_term and part.property_payment_term.id or False
        fiscal_position = part.property_account_position and part.property_account_position.id or False
        dedicated_salesman = part.user_id and part.user_id.id or uid
        
        dsp_price_list_id = part.dsp_price_list_id
        
        val = {
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'payment_term': payment_term,
            'fiscal_position': fiscal_position,
            'user_id': dedicated_salesman,
            'dsp_price_list_id' : dsp_price_list_id, 
            'sale_type' : 'Outlet (Direct Selling)',
            'dsp_price_list_id' : 'real',
        }
        if pricelist:
            val['pricelist_id'] = pricelist
        return {'value': val}
    
    
    _defaults = {
            'dsp_price_list_id' : 'real',
            'sale_type' : 'Outlet (Direct Selling)',  
            'order_policy' : 'On Demand',          
                 }
      
sale_order()

class sale_order_line(osv.osv):
    
    _inherit = "sale.order.line"
    
    _columns = {
            'product_dsp_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True),
            'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True, invisible=True),
            'cons_doc': fields.many2one('stock.picking', 'Internal Moves', domain=[('type', '=', 'internal')]),
                }
    
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        lang = lang or context.get('lang',False)
        if not  partner_id:
            raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
        warning = {}
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        context = {'lang': lang, 'partner_id': partner_id}
        if partner_id:
            lang = partner_obj.browse(cr, uid, partner_id).lang
        context_partner = {'lang': lang, 'partner_id': partner_id}

        if not product:
            return {'value': {'th_weight': 0,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False
        fpos = fiscal_position and self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position) or False
        if update_tax: #The quantity only have changed
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)

        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
            if product_obj.description_sale:
                result['name'] += '\n'+product_obj.description_sale
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}
        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up

        if not uom2:
            uom2 = product_obj.uom_id
        # get unit price

        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
                    'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, {
                        'uom': uom or result.get('product_uom'),
                        'date': date_order,
                        })[pricelist]
            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"            
                
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'domain': domain, 'warning': warning}
    
    def onchange_product_dsp_id(self, cr, uid, ids, product_dsp_id, sale_type, price_list, partner_id, context=None):
        price_unit = 0.0
        discount = 0.0        
        if not product_dsp_id:            
            result = {'value': {
                    'product_id' : product_dsp_id,
                    }
                }            
            return result
        
        partner_id = self.pool.get('res.partner').browse(cr, uid, partner_id, context=None)
        product = self.pool.get('product.template').browse(cr, uid, product_dsp_id, context=None)
            
        if sale_type == 'Promo':
            discount = 100
        else:
            discount = 0                
        
        print product.jkt_cost
        print partner_id.outlet_margin
        print product.real_price        
                
        if price_list == 'real':
            price_unit = product.real_price
        elif price_list == 'outlet':
            price_unit = product.jkt_cost + (product.jkt_cost * partner_id.outlet_margin/ 100)
        
        print price_unit
        
        result = {'value': {
                    'product_id' : product_dsp_id,
                    'price_unit' : price_unit,     
                    'discount'   : discount               
                    }
                } 
        return result 
    
    def onchange_cons_doc(self, cr, uid, ids, cons_doc, product_dsp_id, sale_type, partner_id, context=None):
        result = ''                    
        if not product_dsp_id:
            raise osv.except_osv(_('Warning Confirmation !'), _('Please select the Product first!"'))
            return False            
        elif not partner_id:
            raise osv.except_osv(_('Warning Confirmation !'), _('Please select the Partner first!"'))
            return False
        else:                 
            product = self.pool.get('product.template').browse(cr, uid, product_dsp_id, context=None)                            
            move_line = self.pool.get('stock.picking').browse(cr, uid, cons_doc, context=context).move_lines
            move_name = self.pool.get('stock.move').browse(cr, uid, cons_doc, context=context)            
            for line in move_line:
                if line.name == product.name:
                    result = {'value': {
                        'price_unit' : line.price_unit,                            
                        }
                    }                        
                else:
                    raise osv.except_osv(_('Warning Confirmation !'), _('This Internal moves has no line contains the product!"'))
                    result = {'value': {
                        'price_unit' : 0,                            
                        }
                    }                                                                           
        return result            
            
sale_order_line()