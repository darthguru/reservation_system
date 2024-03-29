# Copyright (c) 2022, ajay patole and contributors
# For license information, please see license.txt

import frappe
import logging
from frappe.model.document import Document
from frappe.utils  import getdate,nowdate,flt
from frappe.model.mapper import get_mapped_doc

# logging.basicConfig(filename='reservation_log.txt',level=logging.DEBUG,format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
# logging.debug('debug info')

class ReservationSchedule(Document):
	def validate(self):
		self.check_reserve_till()
		self.restrict_duplicate_item_reservaton()

		flag = 1
		for i in self.items:
			if i.delivered_qty != i.qty:
				flag = 0
		if flag == 0 and self.docstatus == 1:
			self.status = 'Open'

		self.db_set('status',self.status)

	def on_cancel(self):
		self.status = 'Cancelled'
		self.db_set('status',self.status)
		
	def before_submit(self):
		self.reserve_qty()

	def before_save(self):
		pass

	def on_update(self):
		pass

	# Restricting to select past date
	def check_reserve_till(self):
		if self.reserve_till and (getdate(self.reserve_till) < getdate(nowdate())):
			frappe.throw("Reserve date cannot be past date")

	# Restricting duplicate item reservation against same so_number
	def restrict_duplicate_item_reservaton(self):
		print('------------------------------ restrict_duplicate_item_reservaton ---------------------------------------------------')
		if self.so_number:
			item_list = []
			for i in self.items:
				item_code = i.item_code
				so_number = self.so_number

				items = frappe.db.sql(f"""
										SELECT item_code, so_detail FROM `tabReservation Schedule Item`
										WHERE
										item_code = '{item_code}' AND
										so_detail = '{so_number}' AND
										(
											SELECT docstatus from `tabReservation Schedule` 
											WHERE name = `tabReservation Schedule Item`.parent
										) = 1
									""",as_dict=1)

				# This condition is define to collect all items in a list which are already reserve with same so_number	
				if len(items) != 0:
					if items[0].item_code == item_code and items[0].so_detail == so_number:
						item_list.append(items[0].item_code)
				else:
					continue

			message = f"{' - '.join(item_list)} items already reserve against the same sales order"

			# Again Define to print error message
			if len(items) != 0:
					if items[0].item_code == item_code and items[0].so_detail == so_number:
						frappe.throw(message)

	def reserve_qty(self):
		print('---------------------------------------------------reserve_qty------------------------------------------------------------')
		if self.so_number:
			#Pulled so_date for priority at the time of GRN
			pulled_so_date_and_name = frappe.db.sql(f"""
											SELECT name,item_code,qty,creation from `tabSales Order Item`
											WHERE
											parent = '{self.so_number}'
											ORDER BY idx
										""",as_dict=1)
			self.so_date = pulled_so_date_and_name[0].creation

			# logging.info('pulled_so_date_and_name')
			# logging.debug(pulled_so_date_and_name)

			print('pulled_so_date_and_name: ',pulled_so_date_and_name)

			for i in self.items:
				i.so_detail = self.so_number
				reserve_item(i, self.parent_warehouse)

def check_item_in_warehouse(parent_warehouse,item_code):
	data = frappe.db.sql(f"""
								SELECT item_code, SUM(actual_qty) as actual_qty
								FROM `tabBin` 
								WHERE `tabBin`.warehouse 
								IN (
									SELECT name FROM `tabWarehouse` WHERE 
									`tabWarehouse`.parent_warehouse = '{parent_warehouse}'
									)
								AND `tabBin`.item_code = '{item_code}'
							""",as_dict=1)
	# logging.info('check_item_in_warehouse:data')
	# logging.debug(data)
	return data

def already_allocated_qty(item_code,parent_warehouse):
	allocated_reserve_qty = frappe.db.sql(f"""
											SELECT rsi.item_code, SUM(rsi.reserve_qty) AS reserve_qty
											FROM `tabReservation Schedule Item` AS rsi
											JOIN `tabReservation Schedule` AS rs
											ON rsi.parent = rs.name
											WHERE rsi.item_code = '{item_code}'
											AND
											rs.parent_warehouse = '{parent_warehouse}'
											AND
											(select status from `tabReservation Schedule` As rs WHERE rs.name = rsi.parent) = 'Open'
										""",as_dict=1)
	print('allocated_reserve_qty : ',allocated_reserve_qty)

	# logging.info('allocated_reserve_qty')
	# logging.debug(allocated_reserve_qty)

	if allocated_reserve_qty[0].reserve_qty == None:
		allocated_reserve_qty[0].item_code = item_code
		allocated_reserve_qty[0].reserve_qty = 0.0

	already_allocated = allocated_reserve_qty[0].reserve_qty
	# logging.info('already_allocated')
	# logging.debug(already_allocated)
	return already_allocated

def reserve_item(item, parent_warehouse):
	print('------------------------------------------------- reserve_item ----------------------------------------------------------')
	def set_status(doc_no):
		rs = frappe.get_doc('Reservation Schedule',doc_no)
		flag = 1
		for i in rs.items:
			if i.qty != i.delivered_qty:
				flag = 0
		if flag == 1:
			rs.db_set('status','Complete')
		else:
			rs.db_set('status','Open')

	actual_qty_in_wh = check_item_in_warehouse(parent_warehouse,item.item_code)[0].actual_qty
	print('actual_qty_in_wh: ',actual_qty_in_wh)

	# logging.info('actual_qty_in_wh')
	# logging.debug(actual_qty_in_wh)

	# If Delivery Note created and items delivered
	delivery_note_items = frappe.db.sql(f"""
										SELECT parent, item_code, SUM(delivered_qty) as qty from `tabSales Order Item`
										WHERE
										item_code = '{item.item_code}'
										AND
										name = '{item.so_item_name}'
										AND
										(
											SELECT docstatus from `tabSales Order`
											WHERE name = `tabSales Order Item`.parent
										) = 1
									""",as_dict=1)
	print('delivery_note_items: ',delivery_note_items)
	qty = delivery_note_items[0].qty # qty -> delivery note item qty
	if qty == None:
		qty = 0.0

	item.db_set('delivered_qty',qty)
	
	already_allocated = already_allocated_qty(item.item_code,parent_warehouse)
	print('already_allocated: ',already_allocated)

	# logging.info('already_allocated')
	# logging.debug(already_allocated)

	if actual_qty_in_wh == None:
		actual_qty_in_wh = 0

	# logging.info('item_code')
	# logging.debug(item.item_code)

	new_wh_qty = actual_qty_in_wh - already_allocated
	print('new_wh_qty : ',new_wh_qty)

	# logging.info('new_wh_qty (actual_qty_in_wh - already_allocated)')
	# logging.debug(new_wh_qty)

	if new_wh_qty > 0 :
		if new_wh_qty > item.qty:
			reserve_qty = item.qty - qty
			item.db_set('reserve_qty',reserve_qty)

			# logging.info('new_wh_qty > item.qty --> reserve_qty')
			# logging.debug(reserve_qty)
		else:
			print('reserve_qty else')
			if item.qty != item.delivered_qty:
				balance_qty = item.qty - item.delivered_qty

				# logging.info('item.qty != item.delivered_qty --> balance_qty')
				# logging.debug(balance_qty)

				reserve_qty = new_wh_qty - balance_qty

				# logging.info('item.qty != item.delivered_qty --> reserve_qty')
				# logging.debug(reserve_qty)

				if reserve_qty <= 0 :
					reserve_qty = new_wh_qty
					item.db_set('reserve_qty',reserve_qty)

					# logging.info('reserve_qty <= 0 --> reserve_qty')
					# logging.debug(reserve_qty)
				else:
					item.db_set('reserve_qty',balance_qty)

					# logging.info('reserve_qty <= 0 else --> reserve_qty')
					# logging.debug(reserve_qty)
			else:
				item.db_set('reserve_qty',0)
	else:
		reserve_qty = 0
		item.db_set('reserve_qty',reserve_qty)

	# logging.info('-------------------------------------------------------------------------')
	set_status(item.parent) # Here we updating the status

# to extract items from database using so_number or quotation
@frappe.whitelist()
def get_items(**args):
	so_number = args.get('so_number')
	quotation = args.get('quotation')
	
	items = []
	if so_number:
		items1 = frappe.db.sql(f"""
								SELECT * FROM `tabSales Order Item` WHERE `tabSales Order Item`.parent='{so_number}'
								ORDER BY idx asc
							""",as_dict=1)

		items = filter(lambda x: x['qty'] != x['delivered_qty'],items1)
		# print(items) # return --> <filter object at 0x7f42283a5ff0> --> list(items) -->[a,b,c,d]

		return list(items)

	if quotation:
		items1 = frappe.db.sql(f"""
								SELECT * FROM `tabQuotation Item` WHERE `tabQuotation Item`.parent='{quotation}'
								ORDER BY idx asc
							""",as_dict=1)

		items = filter(lambda x: x['qty'] != x['delivered_qty'],items1)

		return list(items)

#######################################################################################################################################

# Hook -  This function update the delivered qty in reservation schedule items
def update_delivered_qty(doc,event):
#------------------------------------------------------------- Delivery Note -------------------------------------------------------------
	if doc.voucher_type == 'Delivery Note' and doc.actual_qty < 0:
		print('--------------------------------------------- voucher_type : Delivery Note ----------------------------------------------')

		delivery_note_items = frappe.db.sql(f"""
												SELECT name, item_code, qty, against_sales_order,so_detail,warehouse as bin_warehouse,
												(
													SELECT parent_warehouse FROM `tabWarehouse`
													WHERE
													name = '{doc.warehouse}'
												) AS parent_warehouse
												FROM `tabDelivery Note Item`
												WHERE
												name = '{doc.voucher_detail_no}'
									""",as_dict=1)[0]
		print('delivery_note_items: ',delivery_note_items)

		against_sales_order = delivery_note_items.against_sales_order

		def delivery_note_without_reservation_schedule(item_code,warehouse):
			reservation_schedule_items = frappe.db.sql(f"""
															SELECT rs.name, rsi.item_code, rsi.qty, SUM(rsi.reserve_qty) AS reserve_qty FROM `tabReservation Schedule Item` rsi 
															JOIN
															`tabReservation Schedule` rs
															ON
															rs.name = rsi.parent
															WHERE
															rsi.item_code = '{item_code}'
															AND
															rs.parent_warehouse = '{warehouse}'
															AND
															(select status from `tabReservation Schedule` As rs WHERE rs.name = rsi.parent) = 'Open'
														""",as_dict=1)[0]
									
			if reservation_schedule_items.item_code != None:
				rs_qty = reservation_schedule_items.qty
				rs_reserve_qty = reservation_schedule_items.reserve_qty

				item_qty_in_wh = frappe.db.sql(f"""
													SELECT item_code, SUM(actual_qty) as actual_qty
													FROM `tabBin`
													WHERE `tabBin`.warehouse
													IN (
														SELECT name FROM `tabWarehouse` WHERE 
														`tabWarehouse`.parent_warehouse = '{warehouse}'
														)
													AND `tabBin`.item_code = '{item_code}'
												""",as_dict=1)[0]
		
				item_qty_in_wh = item_qty_in_wh.actual_qty

				open_qty = item_qty_in_wh - rs_reserve_qty

				if open_qty <= 0:
					msg = f'{delivery_note_items.qty} Unit of Item Code : {item_code} needed in Warehouse - (Some Qty Reserve in Reservation Schedule)'
					frappe.throw(msg)
				else:
					if open_qty < delivery_note_items.qty:
						msg = f'{delivery_note_items.qty - open_qty} Unit of Item Code : {item_code} needed in Warehouse - (Some Qty Reserve in Reservation Schedule)'
						frappe.throw(msg)

		if against_sales_order != None:
			reservation_schedule_items = frappe.db.sql(f"""
															SELECT name, parent, item_code, qty, delivered_qty, reserve_qty from `tabReservation Schedule Item`
															WHERE
															so_item_name = '{delivery_note_items.so_detail}'
															AND
															(select status from `tabReservation Schedule` as rs WHERE rs.name = `tabReservation Schedule Item`.parent) = 'Open'
														""",as_dict=1)
			if len(reservation_schedule_items) != 0:
				reservation_schedule_items = reservation_schedule_items[0]

				frappe.db.set_value('Reservation Schedule Item', reservation_schedule_items.name, 'delivered_qty', reservation_schedule_items.delivered_qty - doc.actual_qty)

				rsi_doc = frappe.get_doc('Reservation Schedule Item', reservation_schedule_items.name )

				reserve_item(rsi_doc, delivery_note_items.parent_warehouse)
			else:
				delivery_note_without_reservation_schedule(doc.item_code,delivery_note_items.parent_warehouse)
		else:
			delivery_note_without_reservation_schedule(doc.item_code,delivery_note_items.parent_warehouse)

#------------------------------------------------------------- Sales Invoice -------------------------------------------------------------
	if doc.voucher_type == 'Sales Invoice':
		print('--------------------------------------------- voucher_type : Sales Invoice ----------------------------------------------')

		sales_invoice_items = frappe.db.sql(f"""
												SELECT name, item_code, qty, sales_order,so_detail,warehouse as bin_warehouse,
												(
													SELECT parent_warehouse FROM `tabWarehouse`
													WHERE
													name = '{doc.warehouse}'
												) AS parent_warehouse
												FROM `tabSales Invoice Item`
												WHERE
												name = '{doc.voucher_detail_no}'
									""",as_dict=1)[0]
		print('delivery_note_items: ',sales_invoice_items)

		sales_order = sales_invoice_items.sales_order
 
		def sales_invoice_without_reservation_schedule(item_code,warehouse):
			reservation_schedule_items = frappe.db.sql(f"""
															SELECT rs.name, rsi.item_code, rsi.qty, SUM(rsi.reserve_qty) AS reserve_qty FROM `tabReservation Schedule Item` rsi 
															JOIN
															`tabReservation Schedule` rs
															ON
															rs.name = rsi.parent
															WHERE
															rsi.item_code = '{item_code}'
															AND
															rs.parent_warehouse = '{warehouse}'
															AND
															(select status from `tabReservation Schedule` As rs WHERE rs.name = rsi.parent) = 'Open'
														""",as_dict=1)[0]

			if reservation_schedule_items.item_code != None:
				rs_qty = reservation_schedule_items.qty
				rs_reserve_qty = reservation_schedule_items.reserve_qty

				item_qty_in_wh = frappe.db.sql(f"""
													SELECT item_code, SUM(actual_qty) as actual_qty
													FROM `tabBin`
													WHERE `tabBin`.warehouse
													IN (
														SELECT name FROM `tabWarehouse` WHERE 
														`tabWarehouse`.parent_warehouse = '{warehouse}'
														)
													AND `tabBin`.item_code = '{item_code}'
												""",as_dict=1)[0]

				item_qty_in_wh = item_qty_in_wh.actual_qty

				open_qty = item_qty_in_wh - rs_reserve_qty

				if open_qty <= 0:
					msg = f'{sales_invoice_items.qty} Unit of Item Code : {item_code} needed in Warehouse - (Some Qty Reserve in Reservation Schedule)'
					frappe.throw(msg)
				else:
					if open_qty < sales_invoice_items.qty:
						msg = f'{sales_invoice_items.qty - open_qty} Unit of Item Code : {item_code} needed in Warehouse - (Some Qty Reserve in Reservation Schedule)'
						frappe.throw(msg)

		if sales_order != None:
			reservation_schedule_items = frappe.db.sql(f"""
															SELECT name, parent, item_code, qty, delivered_qty, reserve_qty from `tabReservation Schedule Item`
															WHERE
															so_item_name = '{sales_invoice_items.so_detail}'
															AND
															(select status from `tabReservation Schedule` as rs WHERE rs.name = `tabReservation Schedule Item`.parent) = 'Open'
														""",as_dict=1)
			if len(reservation_schedule_items) != 0:
				reservation_schedule_items = reservation_schedule_items[0]

				frappe.db.set_value('Reservation Schedule Item', reservation_schedule_items.name, 'delivered_qty', reservation_schedule_items.delivered_qty - doc.actual_qty)

				rsi_doc = frappe.get_doc('Reservation Schedule Item', reservation_schedule_items.name )

				reserve_item(rsi_doc, sales_invoice_items.parent_warehouse)
			else:
				sales_invoice_without_reservation_schedule(doc.item_code,sales_invoice_items.parent_warehouse)
		else:
			sales_invoice_without_reservation_schedule(doc.item_code,sales_invoice_items.parent_warehouse)

#------------------------------------------------------- Purchase Receipt Items (GRN) ----------------------------------------------------
	if doc.voucher_type == 'Purchase Receipt':
		print('------------------------------------- voucher_type : Purchase Reciept ------------------------------------------')
		sl_item_code = doc.item_code
		sl_qty1 = doc.actual_qty
		sl_warehouse = doc.warehouse
		sl_qty = sl_qty1

		# print('sl_item_code: ',sl_item_code,'sl_qty: ',sl_qty, 'sl_warehouse: ',sl_warehouse)
		# logging.info('inside purchase receipt function:doc')
		# logging.debug(doc)
		parent_warehouse_name = frappe.db.sql(f"""
												SELECT parent_warehouse FROM `tabWarehouse`
												WHERE
												name = '{sl_warehouse}'
											""",as_dict=1)[0]

		reservation_schedule_doc = frappe.db.sql(f"""
													SELECT rsi.name, rsi.item_code, rsi.parent, rsi.qty, rsi.reserve_qty, rsi.delivered_qty, rsi.so_detail, rs.so_date, rs.parent_warehouse
													FROM `tabReservation Schedule Item` AS rsi
													JOIN `tabReservation Schedule` As rs
													ON rsi.parent = rs.name
													WHERE (select status from `tabReservation Schedule` As rs WHERE rs.name = rsi.parent) = 'Open'
													AND item_code = '{sl_item_code}'
													AND parent_warehouse = '{parent_warehouse_name.parent_warehouse}'
													ORDER BY rs.so_date
												""",as_dict=1)
		# print('reservation_schedule_doc : ',reservation_schedule_doc)

		# logging.info('reservation_schedule_doc')
		# logging.debug(reservation_schedule_doc)

		if len(reservation_schedule_doc) != 0:
			for i in reservation_schedule_doc:
				rs_qty = i.qty
				rs_reserve_qty = float(i.reserve_qty)
				rs_delivered_qty = i.delivered_qty

				new_reserve_qty = rs_qty - (rs_reserve_qty + rs_delivered_qty)
				# print('new_reserve_qty: ',new_reserve_qty)

				if rs_qty != rs_reserve_qty:
					if sl_qty >= new_reserve_qty:
						if new_reserve_qty > 0:
							new_reserve = rs_reserve_qty + new_reserve_qty
							frappe.db.set_value('Reservation Schedule Item',i.name,
												'reserve_qty',new_reserve)
							sl_qty = sl_qty - new_reserve_qty
					else:
						sl_qty2 = rs_reserve_qty + sl_qty
						frappe.db.set_value('Reservation Schedule Item',i.name,
												'reserve_qty',sl_qty2)
						sl_qty = 0.0

# ------------------------------------------------------------ Stock Transfer Entry ------------------------------------------------------
	if doc.voucher_type == 'Stock Entry':
		print('---------------------------------- voucher_type : Stock Transfer Entry -----------------------------------------')

		sle_item_code = doc.item_code
		sle_qty1 = doc.actual_qty
		sle_warehouse = doc.warehouse
		sle_voucher_no = doc.voucher_no

		sle_qty = sle_qty1

		# print('se_voucher_no: ',sle_voucher_no,'se_item_code: ',sle_item_code,'se_qty: ',sle_qty,'sle_warehouse:',sle_warehouse)

		parent_warehouse_name = frappe.db.sql(f"""
												SELECT parent_warehouse FROM `tabWarehouse`
												WHERE
												name = '{sle_warehouse}'
											""",as_dict=1)[0]
		# print('parent_warehouse_name: ',parent_warehouse_name)
 
		reservation_schedule_doc = frappe.db.sql(f"""
													SELECT rsi.name, rsi.item_code, rsi.qty, rsi.reserve_qty, rsi.reserve_qty, rsi.delivered_qty, rsi.so_detail, rs.so_date
													FROM `tabReservation Schedule Item` AS rsi
													JOIN `tabReservation Schedule` As rs
													ON rsi.parent = rs.name
													WHERE
													(select status from `tabReservation Schedule` As rs WHERE rs.name = rsi.parent) = 'Open'
													AND item_code = '{sle_item_code}'
													AND parent_warehouse = '{parent_warehouse_name.parent_warehouse}'
													ORDER BY rs.so_date
												""",as_dict=1)
		# print('reservation_schedule_doc : ',reservation_schedule_doc)

		stock_entry_detail = frappe.db.sql(f"""
											SELECT name, item_code, qty, actual_qty, s_warehouse,t_warehouse FROM `tabStock Entry Detail`
											WHERE
											parent = '{sle_voucher_no}'
										""",as_dict=1)[0]

		if stock_entry_detail.s_warehouse:
			s_parent_warehouse_name = frappe.db.sql(f"""
														SELECT parent_warehouse FROM `tabWarehouse`
														WHERE
														name = '{stock_entry_detail.s_warehouse}'
													""",as_dict=1)[0]

		if stock_entry_detail.t_warehouse:
			t_parent_warehouse_name = frappe.db.sql(f"""
														SELECT parent_warehouse FROM `tabWarehouse`
														WHERE
														name = '{stock_entry_detail.t_warehouse}'
													""",as_dict=1)[0]

		if sle_qty > 0:
			if len(reservation_schedule_doc) != 0: # Means There is no open reservation whose status is open
				if reservation_schedule_doc[0].item_code != None:
					if  stock_entry_detail.s_warehouse == None or stock_entry_detail.t_warehouse == None or s_parent_warehouse_name.parent_warehouse == t_parent_warehouse_name.parent_warehouse: #second and third condition for Repacking
						frappe.msgprint('Stock Transfer Within Parent')
					else:
						for i in reservation_schedule_doc:
							rs_qty = float(i.qty)
							rs_reserve_qty = float(i.reserve_qty)
							rs_delivered_qty = float(i.delivered_qty)

							new_reserve_qty = rs_qty - (rs_reserve_qty + rs_delivered_qty)

							if rs_qty != rs_reserve_qty:
								if sle_qty >= new_reserve_qty:
									if new_reserve_qty > 0 :
										new_reserve = rs_reserve_qty + new_reserve_qty
										frappe.db.set_value('Reservation Schedule Item', i.name,
															'reserve_qty',new_reserve)
										sle_qty = sle_qty - new_reserve_qty
								else:
									sle_qty2 = rs_reserve_qty + sle_qty
									frappe.db.set_value('Reservation Schedule Item',i.name,
														'reserve_qty',sle_qty2)
									sle_qty = 0.0
			else:
				if len(reservation_schedule_doc) != 0: # Means There is no reservation whose status = open
					if reservation_schedule_doc[0].item_code != None: # if transfer item not present in reservation schedule document
						rs_qty = float(reservation_schedule_doc[0].qty)
						rs_reserve_qty = float(reservation_schedule_doc[0].reserve_qty)

						actual_qty_in_wh = stock_entry_detail.actual_qty
						open_qty = actual_qty_in_wh - rs_reserve_qty

						if open_qty < 0 :
							open_qty = 0
							msg = f'{open_qty} qty are allowed for Transfer'
							frappe.throw(msg)
						else:
							if open_qty < -(sle_qty):
								msg = f'Only {open_qty} qty are allowed for Transfer'
								frappe.throw(msg)

#######################################################################################################################################

#----------------------------------------------------------Hook on_cancel: Purchase Receipt------------------------------------------------
def recalculate_reserve_qty_for_pr(doc,event):
	print('---------------------------------- recalculate_reserve_qty_for_pr ------------------------------------------------------------')
	print('purchase receipt doc: ',doc)
	purchase_receipt_item = frappe.db.sql(f"""
											SELECT item_code, qty, 
											(
												SELECT parent_warehouse FROM `tabWarehouse`
												WHERE
												name = '{doc.set_warehouse}'
											) AS parent_warehouse
											FROM `tabPurchase Receipt Item`
											WHERE parent = '{doc.name}'
										""",as_dict=1)
	print('Purchase Reciept Item -->',purchase_receipt_item)

	for i in purchase_receipt_item:
		reservation_schedule_doc = frappe.db.sql(f"""
													SELECT rsi.name, rsi.item_code, rsi.qty, rsi.reserve_qty, rsi.delivered_qty, rsi.so_detail, rs.so_date, rs.parent_warehouse
													FROM `tabReservation Schedule Item` AS rsi
													JOIN `tabReservation Schedule` As rs
													ON rsi.parent = rs.name
													WHERE (select status from `tabReservation Schedule` As rs WHERE rs.name = rsi.parent) = 'Open'
													AND item_code = '{i.item_code}'
													AND parent_warehouse = '{i.parent_warehouse}'
													ORDER BY rs.so_date
												""",as_dict=1)
		print('reservation_schedule_doc: ',reservation_schedule_doc)

		for k in reservation_schedule_doc:
			frappe.db.set_value('Reservation Schedule Item',k.name,'reserve_qty',0)

		for j in reservation_schedule_doc:
			rsi_doc = frappe.get_doc('Reservation Schedule Item',j.name)
			reserve_item(rsi_doc, j.parent_warehouse)

#---------------------------------------------------------- Hook on_cancel: Delivery Note ------------------------------------------------
def recalculate_reserve_qty_for_dn(doc,event):
	print('-------------------------------------------- recalculate_reserve_qty_for_dn_cancel ---------------------------------------------')
	def update_status(doc):
		rs = frappe.get_doc('Reservation Schedule',doc)
		flag = 1
		for i in rs.items:
			if i.delivered_qty != i.qty:
				flag = 0
		if flag == 0 and rs.docstatus == 1:
			rs.status = 'Open'

		rs.db_set('status',rs.status)

	delivery_note_all_item = frappe.db.sql(f"""
											SELECT item_code, qty, warehouse, against_sales_order,warehouse
											FROM `tabDelivery Note Item`
											WHERE parent = '{doc.name}'
										""",as_dict=1)
	print('delivery_note_all_item -->',delivery_note_all_item)

	for i1 in delivery_note_all_item:
		parent_warehouse_name = frappe.db.sql(f"""
													SELECT parent_warehouse FROM `tabWarehouse`
													WHERE
													name = '{i1.warehouse}'
												""",as_dict=1)[0]
		print('parent_warehouse_name: ',parent_warehouse_name)
		parent_warehouse = parent_warehouse_name.parent_warehouse

		for i in delivery_note_all_item:
			reservation_schedule_doc = frappe.db.sql(f"""
														SELECT rsi.name, rsi.parent, rsi.item_code, rsi.qty, rsi.reserve_qty, rsi.delivered_qty, rsi.so_detail, rs.so_date, rs.parent_warehouse
														FROM `tabReservation Schedule Item` AS rsi
														JOIN `tabReservation Schedule` As rs
														ON rsi.parent = rs.name
														WHERE 
														so_detail = '{i.against_sales_order}'
														AND item_code = '{i.item_code}'
														AND parent_warehouse = '{parent_warehouse}'
														AND rs.status != 'cancelled'
														ORDER BY rs.so_date
													""",as_dict=1)
			print('reservation_schedule_doc: ',reservation_schedule_doc)

			for k in reservation_schedule_doc:
				frappe.db.set_value('Reservation Schedule Item',k.name,'reserve_qty',0)
				frappe.db.set_value('Reservation Schedule Item',k.name,'delivered_qty',0)

			for j in reservation_schedule_doc:
				rsi_doc = frappe.get_doc('Reservation Schedule Item',j.name)
				reserve_item(rsi_doc, j.parent_warehouse)

		if len(reservation_schedule_doc) != 0:
			update_status(reservation_schedule_doc[0].parent)

#---------------------------------------------------------- Hook on_cancel: Stock Transfer Entry (STE) -----------------------------------
def recalculate_reserve_qty_for_stock_entry(doc,event):
	print('--------------------------------------------- recalculate_reserve_qty_for_stock_entry ---------------------------------------------------')
	print('doc: ',doc)

	stock_entry_detail = frappe.db.sql(f"""
										SELECT name, item_code, qty, actual_qty, s_warehouse,t_warehouse
										FROM `tabStock Entry Detail`
										WHERE
										parent = '{doc.name}'
									""",as_dict=1)[0]
	print('stock_entry_detail: ',stock_entry_detail)

	parent_warehouse_name = frappe.db.sql(f"""
											SELECT parent_warehouse FROM `tabWarehouse`
											WHERE
											name = '{stock_entry_detail.t_warehouse}'
										""",as_dict=1)[0]
	print('parent_warehouse_name: ',parent_warehouse_name)

	reservation_schedule_doc = frappe.db.sql(f"""
												SELECT rsi.name, rsi.name , rsi.item_code, rsi.qty, rsi.reserve_qty, rsi.delivered_qty, rsi.so_detail, rs.so_date, rs.parent_warehouse
												FROM `tabReservation Schedule Item` AS rsi
												JOIN `tabReservation Schedule` As rs
												ON rsi.parent = rs.name
												WHERE (select status from `tabReservation Schedule` As rs WHERE rs.name = parent) = 'Open'
												AND item_code = '{stock_entry_detail.item_code}'
												AND parent_warehouse = '{parent_warehouse_name.parent_warehouse}'
												ORDER BY rs.so_date
											""",as_dict=1)
	print('reservation_schedule_doc: ',reservation_schedule_doc)

	for k in reservation_schedule_doc:
		frappe.db.set_value('Reservation Schedule Item',k.name,'reserve_qty',0)

	for j in reservation_schedule_doc:
		rsi_doc = frappe.get_doc('Reservation Schedule Item',j.name)
		reserve_item(rsi_doc, j.parent_warehouse)

########################################################################################################################################

# --------------------------------------- Make Reservation Schedule from Sales Order ---------------------------------------------------
@frappe.whitelist()
def make_reservation_schedule(source_name, target_doc=None, skip_item_mapping=False):
	print('source_name: ',source_name)

	def set_missing_values(source, target):
		target.select = 'SO Number'
		target.so_posting_date = source.transaction_date
		
		target.flags.ignore_permissions = True
		target.run_method("set_missing_values")

	mapper = {
		"Sales Order": {"doctype": "Reservation Schedule", "validation": {"docstatus": ["=", 1]}},
	}
	
	mapper["Sales Order Item"] = {
			"doctype": "Reservation Schedule Item",
			"field_map": {
				"parent": "so_detail",
				"name": "so_item_name"
			},
		}

	target_doc = get_mapped_doc("Sales Order", source_name, mapper, target_doc, set_missing_values)
	
	target_doc.set_onload("ignore_price_list", True)

	return target_doc

# ------------------------------------------- Make Delivery Note from Reservation Schedule ----------------------------------------------
@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, skip_item_mapping=False):
	print('source_name: ',source_name)

	mapper = {
		"Reservation Schedule": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
	} 

	mapper["Reservation Schedule Item"] = {
			"doctype": "Delivery Note Item",
			"field_map": {
				"reserve_qty" : "qty",
				"so_detail": "against_sales_order",
				"so_item_name" : "so_detail"
			},
		}

	target_doc = get_mapped_doc("Reservation Schedule", source_name, mapper, target_doc)
	
	target_doc.set_onload("ignore_price_list", True)

	return target_doc

# ------------------------------------------- Make picklist from Reservation Schedule ---------------------------------------------------
@frappe.whitelist()
def make_pick_list(source_name, target_doc=None, skip_item_mapping=False):
	print('source_name: ',source_name)

	from erpnext.stock.doctype.packed_item.packed_item import is_product_bundle
	source1 = frappe.db.sql(f"""
								SELECT so_detail,
								(
									SELECT parent_warehouse FROM `tabReservation Schedule`
									WHERE
									name = '{source_name}'
								) AS parent_warehouse
								FROM `tabReservation Schedule Item`
								WHERE
								parent = '{source_name}'
							""",as_dict=1)
	
	source= source1[0].so_detail
	parent_warehouse = source1[0].parent_warehouse
	print('source: ',source)

	def update_item_quantity(source, target, source_parent) -> None:
		picked_qty = flt(source.picked_qty) / (flt(source.conversion_factor) or 1)
		qty_to_be_picked = flt(source.qty) - max(picked_qty, flt(source.delivered_qty))

		target.qty = qty_to_be_picked
		target.stock_qty = qty_to_be_picked * flt(source.conversion_factor)

	def should_pick_order_item(item) -> bool:
		return (
			abs(item.delivered_qty) < abs(item.qty)
			and item.delivered_by_supplier != 1
			and not is_product_bundle(item.item_code)
		)

	doc = get_mapped_doc(
		"Sales Order",
		source,
		{
			"Sales Order": {"doctype": "Pick List", "validation": {"docstatus": ["=", 1]}},
			"Sales Order Item": {
				"doctype": "Pick List Item",
				"field_map": {
				"parent": "sales_order",
				"name": "sales_order_item",
				},
				"postprocess": update_item_quantity,
				"condition": should_pick_order_item,
			},
		},
		target_doc,
	)

	doc.purpose = "Delivery"
	doc.parent_warehouse = parent_warehouse

	doc.set_item_locations()

	return doc

###################################################################################################################################

# ------------------------------------------------- Change Status to Hold -----------------------------------------------------------
@frappe.whitelist()
def change_status_to_hold(source_name, target_doc=None, skip_item_mapping=False):
	print('--------------------------------------------- Hold ---------------------------------------------------------------')
	print('source_name: ',source_name)

	rs = frappe.get_doc('Reservation Schedule',source_name)
	rs.db_set('status','Hold',update_modified=True)

	reservation_schedule_items = frappe.db.sql(f"""
												SELECT name, parent, item_code, qty, delivered_qty, reserve_qty from `tabReservation Schedule Item`
												WHERE
												parent = '{source_name}'
												AND
												(select status from `tabReservation Schedule` as rs WHERE rs.name = '{source_name}') = 'Hold'
												""",as_dict=1)
	print('reservation_schedule_item: ',reservation_schedule_items)

	if len(reservation_schedule_items) != 0:
		for i in reservation_schedule_items:
			frappe.db.set_value('Reservation Schedule Item',i.name,'reserve_qty',0)

# ------------------------------------------------- Change Status to Close -----------------------------------------------------------
@frappe.whitelist()
def change_status_to_close(source_name):
	print('----------------------------------------------- Close ---------------------------------------------------------')
	print(source_name)
	rs = frappe.get_doc('Reservation Schedule',source_name)
	rs.db_set('status','Close')

	reservation_schedule_items = frappe.db.sql(f"""
												SELECT name, parent, item_code, qty, delivered_qty, reserve_qty from `tabReservation Schedule Item`
												WHERE
												parent = '{source_name}'
												AND
												(select status from `tabReservation Schedule` as rs WHERE rs.name = '{source_name}') = 'Close'
												""",as_dict=1)
	# print('reservation_schedule_item: ',reservation_schedule_items)
	# frappe.msgprint(reservation_schedule_items)
	if len(reservation_schedule_items) != 0:
		for i in reservation_schedule_items:
			frappe.db.set_value('Reservation Schedule Item',i.name,'reserve_qty',0)

# ------------------------------------------------- Reopen doc whose status hold -----------------------------------------------------
@frappe.whitelist()
def reopen_hold_doc(source_name, parent_warehouse):
	print('----------------------------------------------- Reopen Hold Doc ---------------------------------------------------------')
	reservation_schedule_items = frappe.db.sql(f"""
												SELECT name, parent, item_code, qty, delivered_qty, reserve_qty,warehouse from `tabReservation Schedule Item`
												WHERE
												parent = '{source_name}'
												AND
												(select status from `tabReservation Schedule` as rs WHERE rs.name = '{source_name}') = 'Hold'
												order by idx""",as_dict=1)
	print('reservation_schedule_item: ',reservation_schedule_items)

	if len(reservation_schedule_items) != 0:
		for i in reservation_schedule_items:
			rs = frappe.get_doc('Reservation Schedule Item',i.name)
			reserve_item(rs,parent_warehouse)

# ------------------------------------------------- Reopen doc whose status hold ------------------------------------------------------
@frappe.whitelist()
def reopen_close_doc(source_name, parent_warehouse):
	print('-----------------------------------------------Reopen Close Doc---------------------------------------------------------')
	print(source_name)
	reservation_schedule_items = frappe.db.sql(f"""
												SELECT name, parent, item_code, qty, delivered_qty, reserve_qty,warehouse from `tabReservation Schedule Item`
												WHERE
												parent = '{source_name}'
												AND
												(select status from `tabReservation Schedule` as rs WHERE rs.name = '{source_name}') = 'Close'
												order by idx""",as_dict=1)
	print('reservation_schedule_item: ',reservation_schedule_items)

	if len(reservation_schedule_items) != 0:
		for i in reservation_schedule_items:
			rs = frappe.get_doc('Reservation Schedule Item',i.name)
			reserve_item(rs,parent_warehouse)
	
######################################################################################################################################

# HOOK --> on_change(Sales Order Item) this function will call [changes like qty,rate,discount]
@frappe.whitelist()
def on_sales_order_item_update(doc,event):
	
	so_items = get_items(so_number= doc.name)

	reservation_schedule_items = frappe.db.sql(f"""
												SELECT rsi.name, rsi.parent, rsi.item_code, rsi.qty, rsi.delivered_qty, rsi.reserve_qty, rsi.warehouse, rs.parent_warehouse
												FROM `tabReservation Schedule Item` rsi
												JOIN `tabReservation Schedule` rs
												ON rsi.parent = rs.name
												WHERE
												so_detail = '{doc.name}'
												AND
												rs.docstatus = 1
												order by rsi.idx""",as_dict=1)
	print('reservation_schedule_item: ',reservation_schedule_items)

	if len(reservation_schedule_items) != 0:
		for i in so_items:
			frappe.db.sql(f"""
							UPDATE `tabReservation Schedule Item`
							SET
							item_code = '{i.item_code}',
							item_name = '{i.item_name}',
							description = '{i.description}',
							item_group = '{i.item_group}',
							brand = '{i.brand}',
							image = '{i.image}',
							qty = '{i.qty}',
							stock_uom = '{i.stock_uom}',
							uom = '{i.uom}',
							conversion_factor = '{i.conversion_factor}',
							stock_qty = '{i.stock_qty}',
							price_list_rate = '{i.price_list_rate}',
							base_price_list_rate = '{i.base_price_list_rate}',
							margin_type = '{i.margin_type}',
							margin_rate_or_amount = '{i.margin_rate_or_amount}',
							rate_with_margin = '{i.rate_with_margin}',
							discount_percentage = '{i.discount_percentage}',
							discount_amount = '{i.discount_amount}',
							base_rate_with_margin = '{i.base_rate_with_margin}',
							rate = '{i.rate}',
							amount = '{i.amount}',
							item_tax_template = '{i.item_tax_template}',
							base_rate = '{i.base_rate}',
							base_amount = '{i.base_amount}',
							pricing_rules = '{i.pricing_rules}',
							stock_uom_rate = '{i.stock_uom_rate}',
							is_free_item = '{i.is_free_item}',
							grant_commission = '{i.grant_commission}',
							net_rate = '{i.net_rate}',
							net_amount = '{i.net_amount}',
							base_net_rate = '{i.base_net_rate}',
							base_net_amount = '{i.base_net_amount}',
							billed_amt = '{i.billed_amt}',
							valuation_rate = '{i.valuation_rate}',
							gross_profit = '{i.gross_profit}',
							delivered_by_supplier = '{i.delivered_by_supplier}',
							supplier = '{i.supplier}',
							weight_per_unit = '{i.weight_per_unit}',
							total_weight = '{i.total_weight}',
							weight_uom = '{i.weight_uom}',
							warehouse = '{i.warehouse}',
							target_warehouse = '{i.target_warehouse}',
							prevdoc_docname = '{i.prevdoc_docname}',
							against_blanket_order = '{i.against_blanket_order}',
							blanket_order = '{i.blanket_order}',
							blanket_order_rate = '{i.blanket_order_rate}',
							bom_no = '{i.bom_no}',
							projected_qty = '{i.projected_qty}',
							actual_qty = '{i.actual_qty}',
							ordered_qty = '{i.ordered_qty}',
							planned_qty = '{i.planned_qty}',
							work_order_qty = '{i.work_order_qty}',
							delivered_qty = '{i.delivered_qty}',
							produced_qty = '{i.produced_qty}',
							returned_qty = '{i.returned_qty}',
							picked_qty = '{i.picked_qty}',
							additional_notes = '{i.additional_notes}',
							purchase_order_item = '{i.purchase_order_item}',
							so_item_name = '{i.name}'
							WHERE
							so_item_name = '{i.name}'
							AND
							docstatus = 1
						""")
		
		for i in reservation_schedule_items:
			frappe.db.set_value('Reservation Schedule Item',i.name,'reserve_qty',0)
			rs = frappe.get_doc('Reservation Schedule Item',i.name)
			reserve_item(rs,i.parent_warehouse)
