from openerp.osv import fields,osv
import pdb
import pprint
import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp

class sale_shop(osv.osv):
    
    _inherit = "sale.shop"    
    _columns = {
            'outlet'       : fields.many2one('res.partner', 'Outlet/Customer', domain=[('customer', '=', True)]),                        
                }
                    
sale_shop()

class sale_order(osv.osv):
    _inherit = "sale.order"
    _description = "Sales Order Inherit DSP"
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'total_fee' : 0.0,
            }
            val = val1 = val2 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(cr, uid, line, context=context)
                val2 += (line.fee * line.product_uom_qty)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
            res[order.id]['total_fee'] = val2
        return res
                
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()
    
    def action_confirm_quotation(self, cr, uid, ids, context=None):        
        return self.write(cr, uid, ids, {'state': 'quotation_confirm'})        
    
    def _prepare_order_picking(self, cr, uid, order, context=None):        
        pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
        current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        sale_type = order.sale_type
        
        print "aaaaaaaaaaaaaaaaaaaaa" , current_user.name
        
        if sale_type == 'Consignment':
            sale_type = 'Consignment'
        elif sale_type == 'Direct Selling':
            sale_type = 'Direct Selling'
        else:
            sale_type = 'FOC'            
        
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
        }    
    
    _columns ={
               'payment_term'           : fields.many2one('account.payment.term', 'Payment Term', required = True),
               'partner_id'             : fields.many2one('res.partner', 'Outlet/Customer', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, change_default=True, select=True, track_visibility='always'),
               'sale_type'              : fields.selection([('FOC', 'FOC'), ('Consignment', 'Consignment'),('Direct Selling','Direct Selling') ], 'Sale Type'),
               'person_name'            : fields.char('Person Name', size=128),
               'date_confirmed'         : fields.date('Input Date'),
               'file_confirmed'         : fields.binary('Quotation File'),
               'person_name_order'      : fields.char('Person Name', size=128),
               'date_confirmed_order'   : fields.date('Input Date'),
               'file_confirmed_order'   : fields.binary('Sales Order File'),
               'dsp_price_list_id'      : fields.selection([('Real Price', 'Real Price'), ('Outlet Price', 'Outlet Price')], 'DSP Price List'),
               
               'total_fee' : fields.function(_amount_all, string='Total Misc. Fee', digits_compute=dp.get_precision('Account'), 
                    store={
                        'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                        'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
                    },
                    multi='sums', help="The amount without tax.", track_visibility='always'),                                                          
               'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
                    store={
                        'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                        'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
                    },
                    multi='sums', help="The amount without tax.", track_visibility='always'),
               'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
                    store={
                        'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                        'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
                    },
                    multi='sums', help="The tax amount."),
               'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
                    store={
                        'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                        'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
                    },
                    multi='sums', help="The total amount."),                                             
               'state': fields.selection([
                    ('draft', 'Draft Quotation'),
                    ('sent', 'Quotation Sent'),
                    ('cancel', 'Cancelled'),
                    ('waiting_date', 'Waiting Schedule'),
                    ('quotation_confirm', 'Quotation Confirmed'),                    
                    ('progress', 'Sales Order'),
                    ('order_confirm', 'Order Confirmed'),
                    ('manual', 'Sale to Invoice'),
                    ('shipping_except', 'Shipping Exception'),
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
            'price_unit': line.price_unit,
            'price_unit_view': line.price_unit,
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
        invoice_search  = self.pool.get('account.invoice').search(cr, uid, [('state','=','open')], context=None)                            
        # Get the list of open invoice                        
        invoice_obj = self.pool.get('account.invoice').browse(cr, uid, invoice_search, context=None)            
        
        #=======================================================================
        # for inv in invoice_obj1:            
        #     if inv.partner_id.parent_id.id == partner_id:
        #         if partner_bypass == False:                                                
        #             raise osv.except_osv(('Outstanding Payment!'),('You cannot save if outlet have outstanding payment!'))
        #         elif partner_bypass == True:
        #             res_partner.write(cr, uid, partner_id, {'bypass_order' : False})
        #=======================================================================
                            
        # check due date of every single open invoice if there's any of them        
        if invoice_obj:
            for inv in invoice_obj:       
                if inv.partner_id.parent_id.id == partner_id:         
                    d1 = datetime.strptime(date_today, fmt)
                    d2 = datetime.strptime(inv.date_due, fmt)                
                    daysDiff = int((d1-d2).days) 
                                      
                    if daysDiff >= 0:  
                        print daysDiff                  
                        if partner_bypass == False:                                                
                            raise osv.except_osv(('Outstanding Payment!'),('You cannot save if outlet have outstanding payment!'))
                        elif partner_bypass == True:
                            res_partner.write(cr, uid, partner_id, {'bypass_order' : False})
                    else:
                        print "out"
        
        #=======================================================================
        # if invoice_obj:                
        #     if partner_bypass == False:                                                
        #         raise osv.except_osv(('Outstanding Payment!'),('You cannot save if outlet have outstanding payment!'))
        #     elif partner_bypass == True:
        #         res_partner.write(cr, uid, partner_id, {'bypass_order' : False})
        # else:
        #     print "out"
        #=======================================================================
                                                                                                                                                                
        ###############################################                        
        #=======================================================================
        # for n in range(len(vals.get('order_line'))):            
        #     order_line_id = vals.get('order_line')            
        #     prod_id = order_line_id[n][2]['product_id']            
        #     print "yihaaaaaaaaaaaaaaaA", prod_id      
        #     partner_id = vals.get('partner_id')            
        #=======================================================================
            
            #===================================================================
            # partner_obj = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            # products = self.pool.get('product.product').browse(cr, uid, prod_id, context=None)            
            # country = products.country_id.name                                                        
            # outlet_disc_id = self.pool.get('outlet.discount').search(cr, uid, [('outlet_id','=', partner_id),('country_id', '=', country)], context=None)
            # if outlet_disc_id:
            #     outlet_disc_obj = self.pool.get('outlet.discount').browse(cr, uid, outlet_disc_id, context=None)            
            #     discount = outlet_disc_obj[0].discount - partner_obj.consignment_discount
            #     print "ssssssssssssssssssssss", discount                    
            #               
            # if bool(vals['order_line'][n][2]):
            #     vals['order_line'][n][2]['discount']= discount  
            #===================================================================
                        
        for n in range(len(vals.get('order_line'))):
            fee = vals['order_line'][n][2]['fee']                                

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
    
    def onchange_partner_id_dsp(self, cr, uid, ids, sale_type, part, context=None):
        shop_default = ''        
        if not part:
            return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False,  'payment_term': False, 'fiscal_position': False}}

        part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
        addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        payment_term = part.property_payment_term and part.property_payment_term.id or False
        fiscal_position = part.property_account_position and part.property_account_position.id or False
        dedicated_salesman = part.user_id and part.user_id.id or uid        
        
        partner_name = part.name            
        if sale_type == 'Consignment':                           
            shop_id = self.pool.get('sale.shop').search(cr, uid, [('outlet','=',partner_name)], context=context)        
            shop_obj = self.pool.get('sale.shop').browse(cr, uid, shop_id, context=context)
            for shop in shop_obj:                                  
                shop_default = shop.id        
                                                                                                        
            val = {
                'partner_invoice_id': addr['invoice'],
                'partner_shipping_id': addr['delivery'],
                'payment_term': payment_term,
                'fiscal_position': fiscal_position,
                'user_id': dedicated_salesman,                                             
                'shop_id'   : shop_default,                            
                }
            
        else:                                                                                                                   
            val = {
                'partner_invoice_id': addr['invoice'],
                'partner_shipping_id': addr['delivery'],
                'payment_term': payment_term,
                'fiscal_position': fiscal_position,
                'user_id': dedicated_salesman,                                                         
                }
            
        if pricelist:
            val['pricelist_id'] = pricelist
        return {'value': val}
    
    def onchange_sale_type(self, cr, uid, ids, sale_type, partner_id, context=None):
        val = {}
        order = self.pool.get('sale.order')
        shop_id = self.pool.get('sale.shop').search(cr, uid, [('outlet','=',partner_id)], context=context)        
        shop_obj = self.pool.get('sale.shop').browse(cr, uid, shop_id, context=context)
        
        if sale_type == 'Consignment':
            shop_default = ''                                                                                                                   
            if partner_id:                
                for shop in shop_obj:                                        
                    shop_default = shop.id                                                                     
                        
                val = {                
                    'shop_id'   : shop_default,      
                }        
            else:                
                val = {}
                 
        else:
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
            shop_ids = self.pool.get('sale.shop').search(cr, uid, [('company_id','=',company_id)], context=context)
            if not shop_ids:
                raise osv.except_osv(_('Error!'), _('There is no default shop for the current user\'s company!'))            
                        
            val = {'shop_id' : shop_ids[0]}
                
        return {'value': val}
                    
    _defaults = {
            'dsp_price_list_id' : 'Real Price',
            'sale_type' : 'Direct Selling',  
            'order_policy' : 'On Demand',          
                 }
      
sale_order()

class sale_order_line(osv.osv):
        
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = (line.price_unit * (1 - (line.discount or 0.0) / 100.0)) + line.fee
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)            
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res
    
    def _amount_discount(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}                    
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):                    
            res[line.id] = (line.price_unit * (line.discount or 0.0) / 100.0) - line.fee                                        
        return res
    
    _inherit = "sale.order.line"    
    _columns = {
            'product_dsp_id'    : fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True),
            'product_id'        : fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True, invisible=True),
            'cons_doc'          : fields.many2one('stock.picking', 'Internal Moves', domain=[('type', '=', 'internal')]),
            'jkt_cost'          : fields.float('JKT Cost', digits_compute=dp.get_precision('Product Price')),
            'profit'            : fields.float('Profit', digits_compute=dp.get_precision('Product Price')),
            'sub_profit'        : fields.float('Sub Profit', digits_compute=dp.get_precision('Product Price')),
            'fee'               : fields.float('Misc. Fee', digits_compute=dp.get_precision('Product Price')),
            'total_discount'    : fields.function(_amount_discount, string='Discount Total', digits_compute=dp.get_precision('Product Price')),
            'price_subtotal'    : fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
            'qty_on_hand'       : fields.float('Qty On Hand', digits_compute=dp.get_precision('Product Unit of Measure')),
            'qty_reserved'      : fields.float('Qty Reserved', digits_compute=dp.get_precision('Product Unit of Measure')),
            'discount'          : fields.float('Discount (%)', digits_compute= dp.get_precision('Discount')),            
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
    
    def onchange_product_dsp_id(self, cr, uid, ids, product_dsp_id, product_uom_qty, sale_type, price_list, partner_id, context=None):                    
        price_unit = 0.0
        discount = 0.0        
        stock_default = 0
        profit = 0.0
        sub_profit = 0.0
        if not product_dsp_id:            
            result = {'value': {
                    'product_id' : product_dsp_id,
                    }
                }            
            return result
        
        partner_id = self.pool.get('res.partner').browse(cr, uid, partner_id, context=None)        
        product = self.pool.get('product.template').browse(cr, uid, product_dsp_id, context=None)
        product_product = self.pool.get('product.product').browse(cr, uid, product_dsp_id, context=None)
        
        qty_on_hand = product_product.qty_available
        qty_reserved = product_product.total_reserved
        
        products = self.pool.get('product.product').browse(cr, uid, product_dsp_id, context=None)
        country = products.country_id.name
        print country              
                                
        outlet_disc_id = self.pool.get('outlet.discount').search(cr, uid, [('outlet_id','=',partner_id.id),('country_id', '=', country)], context=None)
        if outlet_disc_id:
            outlet_disc_obj = self.pool.get('outlet.discount').browse(cr, uid, outlet_disc_id, context=None)            
            discount = outlet_disc_obj[0].discount - partner_id.consignment_discount
                
        if sale_type == 'Consignment':            
            stock_search  = self.pool.get('stock.picking').search(cr, uid, [('type','=','internal'),('partner_id', '=', partner_id.id)], context=None)
                    
            min_value = 100000000
            for stock in stock_search:            
                if stock < min_value:
                    min_value = stock
                    
            stock_default = min_value
            
            products = self.pool.get('product.product').browse(cr, uid, product_dsp_id, context=None)
            product = self.pool.get('product.template').browse(cr, uid, product_dsp_id, context=None)                            
            move_line = self.pool.get('stock.picking').browse(cr, uid, stock_default, context=context).move_lines
                        
            for line in move_line:
                if line.name == product.name:
                    price_unit = line.price_unit_view                                        
                else:
                    raise osv.except_osv(_('Warning Confirmation !'), _('This Internal moves has no line contains the product!"'))
                    price_unit = 0                                                                            
        
        else:                                                                                         
            if sale_type == 'FOC':
                discount = 100
            
            profit = (product.real_price - (discount * product.real_price / 100) - product.jkt_cost)
            sub_profit = profit * product_uom_qty        
            price_unit = product.real_price          
            
            if product_product.foc == 'FOC':
                price_unit = 0                      
            
        result = {'value': {
                    'product_id'    : product_dsp_id,
                    'price_unit'    : price_unit,     
                    'discount'      : discount,
                    'jkt_cost'      : product.jkt_cost,
                    'profit'        : profit,
                    'sub_profit'    : sub_profit,
                    'cons_doc'      : stock_default,     
                    'qty_on_hand'   : qty_on_hand,
                    'qty_reserved'  : qty_reserved,                                                                
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
                        'price_unit' : line.price_unit_view,                            
                        }
                    }                        
                else:
                    raise osv.except_osv(_('Warning Confirmation !'), _('This Internal moves has no line contains the product!"'))
                    result = {'value': {
                        'price_unit' : 0,                            
                        }
                    }                                                                           
        return result
    
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        """Prepare the dict of values to create the new invoice line for a
           sales order line. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record line: sale.order.line record to invoice
           :param int account_id: optional ID of a G/L account to force
               (this is used for returning products including service)
           :return: dict of values to create() the invoice line
        """
        print "yesssssssssssssssssssssssssssssssssssss"
        res = {}
        if not line.invoiced:
            if not account_id:
                if line.product_id:
                    account_id = line.product_id.property_account_income.id
                    if not account_id:
                        account_id = line.product_id.categ_id.property_account_income_categ.id
                    if not account_id:
                        raise osv.except_osv(_('Error!'),
                                _('Please define income account for this product: "%s" (id:%d).') % \
                                    (line.product_id.name, line.product_id.id,))
                else:
                    prop = self.pool.get('ir.property').get(cr, uid,
                            'property_account_income_categ', 'product.category',
                            context=context)
                    account_id = prop and prop.id or False
            uosqty = self._get_line_qty(cr, uid, line, context=context)
            uos_id = self._get_line_uom(cr, uid, line, context=context)
            pu = 0.0
            if uosqty:
                pu = round(line.price_unit * line.product_uom_qty / uosqty,
                        self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price'))
            fpos = line.order_id.fiscal_position or False
            account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, account_id)
            if not account_id:
                raise osv.except_osv(_('Error!'),
                            _('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))
                        
            res = {
                'name': line.name,
                'sequence': line.sequence,
                'origin': line.order_id.name,
                'account_id': account_id,
                'price_unit': pu,
                'quantity': uosqty,
                'discount': line.discount,
                'fee' : line.fee,
                'total_discount' : line.total_discount,
                'uos_id': uos_id,
                'product_id': line.product_id.id or False,
                'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
                'account_analytic_id': line.order_id.project_id and line.order_id.project_id.id or False,
                'jkt_cost' : line.jkt_cost
            }

        return res
    
    #===========================================================================
    # def onchange_product_uom_qty(self, cr, uid, ids, product_dsp_id, discount, product_uom_qty, context=None):                            
    #     product = self.pool.get('product.template').browse(cr, uid, product_dsp_id, context=None)                                            
    #     profit = (product.real_price - (discount * product.real_price / 100) - product.jkt_cost)
    #     sub_profit = profit * product_uom_qty        
    #     
    #     result = {'value': {                    
    #                 'sub_profit' : sub_profit                                                    
    #                 }
    #             } 
    #     return result             
    #===========================================================================
            
sale_order_line()