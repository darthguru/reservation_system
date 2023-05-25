# Copyright (c) 2023, ajay patole and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ReservationTransferEntry(Document):
	def validate(self):
		self.validate_transfer_qty()

	def before_submit(self):
		self.add_qty_to_target()
		self.subtract_qty_from_source()

	# validating transfer_qty field
	def validate_transfer_qty(self):
		for row in self.items:
			if row.transfer_qty == None:
				frappe.throw(f"Transfer Qty Should Not be Blank for Item {row.item_code}")
			if int(row.transfer_qty) > int(row.reserve_qty):
				frappe.throw(f'Transfer Qty Should Be Less Than or Equal to Reserve Qty of Item Code {row.item_code}')
			if int(row.transfer_qty) <= 0:
				frappe.throw("Transfer Qty Should be Greater than 0")

		# validating if user enters qty which is greater than target required qty
		if self.target_reservation_no:
			target_res_no = self.target_reservation_no

			for i in self.items:
				res_qty_count = frappe.db.sql(f"""
												SELECT item_code, SUM(qty) as qty,SUM(reserve_qty) as reserve_qty FROM `tabReservation Schedule Item`
												WHERE item_code = '{i.item_code}'
												and parent = '{target_res_no}'
											""",as_dict=1)[0]
				# print('res_qty_count: ',res_qty_count)

				if len(res_qty_count) != 0:
					req = res_qty_count.qty - res_qty_count.reserve_qty
					if int(i.transfer_qty) > req and int(i.reserve_qty) > req:
						frappe.throw(f"Target required only {req} Qty for item {i.item_code} and you entered {i.transfer_qty}")

	# Adding Qty in Targer Reservation
	def add_qty_to_target(self):
		target_res_no = self.target_reservation_no

		target_items = frappe.db.sql(f"""
										SELECT *FROM `tabReservation Schedule Item`
										WHERE parent = '{target_res_no}' ORDER BY idx asc
									""",as_dict=1)
		# print('target_items: ',target_items)
 
		for i in self.items:
			transfer_qty = int(i.transfer_qty)
			for j in target_items:
				if i.item_code == j.item_code:
					req_qty = j.qty - j.reserve_qty
					if req_qty == transfer_qty:
						frappe.db.set_value('Reservation Schedule Item',j.name,'reserve_qty',req_qty+j.reserve_qty)
						frappe.db.commit()
						break
					if req_qty <= transfer_qty:
						remain = transfer_qty - req_qty
						transfer_qty = remain
						frappe.db.set_value('Reservation Schedule Item',j.name,'reserve_qty',req_qty+j.reserve_qty)
						frappe.db.commit()
					else:
						frappe.db.set_value('Reservation Schedule Item',j.name,'reserve_qty',transfer_qty+j.reserve_qty)
						frappe.db.commit()
						break

	# Subtracting Qty from Source Reservation
	def subtract_qty_from_source(self):
		source_res_no = self.source_reservation_no

		source_items = frappe.db.sql(f"""
										SELECT *FROM `tabReservation Schedule Item`
										WHERE parent = '{source_res_no}' ORDER BY idx asc
									""",as_dict=1)
		# print('Source Items: ',source_items)

		for i in self.items:
			transfer_qty = int(i.transfer_qty)
			for j in source_items:
				if i.item_code == j.item_code:
					if transfer_qty >= j.reserve_qty:
						remain = transfer_qty - j.reserve_qty
						transfer_qty = remain
						frappe.db.set_value('Reservation Schedule Item',j.name,'reserve_qty',0)
						frappe.db.commit()
					else:
						new_reseve_qty = j.reserve_qty - transfer_qty
						transfer_qty = 0
						frappe.db.set_value('Reservation Schedule Item',j.name,'reserve_qty',new_reseve_qty)
						frappe.db.commit()

@frappe.whitelist()
def get_items(**args):
	s_reservation_no = args.get('s_res_no')
	t_reservation_no = args.get('t_res_no')
	s_parent_wh = args.get('s_par_wh')
	t_parent_wh = args.get('t_par_wh')

	if s_reservation_no == t_reservation_no:
		frappe.throw("Source and Target Reservation Number Can't be same")
	if s_parent_wh != t_parent_wh:
		frappe.throw('Source and Target Parent Warehouse must be same')

	s_item_code = set()
	t_item_code = set()
	filter_items = []
	if s_reservation_no != None and t_reservation_no != None:
		s_all_items = frappe.db.sql(f"""
								SELECT *FROM `tabReservation Schedule Item` WHERE parent = '{s_reservation_no}' ORDER BY idx ASC
							""",as_dict=1)
		for i in s_all_items:
			s_item_code.add(i.item_code)

		t_all_items = frappe.db.sql(f"""
										SELECT *FROM `tabReservation Schedule Item` WHERE parent = '{t_reservation_no}' ORDER BY idx ASC
									""",as_dict=1)
		for j in t_all_items:
			if j.qty != j.reserve_qty:
				t_item_code.add(j.item_code)

		common_item_code = s_item_code.intersection(t_item_code) # Extracted Common Elements From Source and Target

		for k in common_item_code:
			it = frappe.db.sql(f"""
									SELECT item_code,SUM(qty) AS qty,item_name,description,uom,rate,conversion_factor,SUM(reserve_qty) AS reserve_qty
									FROM `tabReservation Schedule Item`
									WHERE
									item_code = '{k}'
									AND
									parent = '{s_reservation_no}'
								""",as_dict=1)[0]
			filter_items.append(it)

	if len(filter_items)==0:
		frappe.throw("There is no similar items in both the reservation schedule or not sufficient qty available for transfer")

	return filter_items
