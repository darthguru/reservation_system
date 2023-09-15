import frappe
import json
import logging
from frappe.utils.nestedset import get_descendants_of

#------------------------------- custome_picklist ---------------------------------------------------
# This Function Subtract The Reserve Qty and Populate the item in Pick List -> locations
# Call -- Sales Order -> create -> Pick List -> Select Parent Warehouse -> Get Item Locations
# Code -- Client Script List-> Pick List -> get_item_locations:

@frappe.whitelist()
def custome_picklist(doc):
    # logging.basicConfig(filename='custome_piclist.txt', level=logging.DEBUG, format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S') # file mode --> filemode='w'
    doc = json.loads(doc)
    # print('doc: ',doc)
    # logging.info('doc')
    # logging.debug(doc)

    locations = doc.get('locations')
    # print('locations: ',locations)

    filter_items = {}
    filter_item_code = []
    filter_doc_locations = []
    my_picklist = []

    def check_item_in_warehouse(parent_warehouse,item_code):
        actual_qty = frappe.db.sql(f"""
                                        SELECT item_code, SUM(actual_qty) as actual_qty
                                        FROM `tabBin`
                                        WHERE `tabBin`.warehouse
                                        IN (
                                            SELECT name FROM `tabWarehouse` WHERE
                                            `tabWarehouse`.parent_warehouse = '{parent_warehouse}'
                                            )
                                        AND `tabBin`.item_code = '{item_code}'
                                    """,as_dict=1)[0]
        # logging.info('actual_qty')
        # logging.debug(actual_qty)

        return actual_qty

    def get_parent_warehouse(warehouse):
        parent_warehouse_name = frappe.db.sql(f"""
                                                SELECT parent_warehouse FROM `tabWarehouse`
                                                WHERE
                                                name = '{warehouse}'
                                            """,as_dict=1)[0]
        return parent_warehouse_name.parent_warehouse

    # here we extracting unique item_code, actual_qty in warehouse and open_qty = actual_qty_in_wh - reserve_qty
    for row in locations:
        item_code = row['item_code']
        warehouse = row['warehouse']

        parent_warehouse_name = get_parent_warehouse(warehouse)

        actual_qty_in_wh1 = check_item_in_warehouse(parent_warehouse_name,item_code)
        if actual_qty_in_wh1.item_code != None:
            actual_qty_in_wh = actual_qty_in_wh1.actual_qty
        else:
            actual_qty_in_wh = 0
        print('actual_qty_in_wh: ',actual_qty_in_wh)

        reserve = frappe.db.sql(f"""
                                    select item_code,sum(reserve_qty) as reserve_qty,rs.parent_warehouse from `tabReservation Schedule Item` rsi
                                    join `tabReservation Schedule` rs
                                    on rs.name = rsi.parent
                                    where rsi.item_code = '{item_code}'
                                    and rs.parent_warehouse = '{parent_warehouse_name}'
                                    and (select status from `tabReservation Schedule` As rs WHERE rs.name = rsi.parent) = 'Open'
                                """,as_dict=1)[0]
        print('reserve: ',reserve)

        if reserve.item_code != None:
            reserve_qty = reserve.reserve_qty
        else:
            my_picklist.append(row)
            continue
        print('reserve_qty: ',reserve_qty)

        open_qty = actual_qty_in_wh - reserve_qty
        print('open_qty: ',open_qty)
        # logging.info('open_qty')
        # logging.debug(open_qty)

        if open_qty > 0 :
            if item_code not in filter_items:
                filter_items[item_code] = {'item_code': item_code, 'actual_qty_in_wh': actual_qty_in_wh, 'open_qty': open_qty}
                filter_item_code.append(item_code)
            filter_doc_locations.append(row)

    print('filter_item_code: ',filter_item_code)
    print('filter_items: ',filter_items)
    print('filter_doc_locations: ',filter_doc_locations)

    # logging.info('filter_item_code')
    # logging.debug(filter_item_code)

    # logging.info('filter_items')
    # logging.debug(filter_items)

    # logging.info('filter_doc_locations')
    # logging.debug(filter_doc_locations)

    for i in filter_item_code:
        item_code_2 = i
        temp = filter_items.get(item_code_2)
        open_qty_2 = temp['open_qty']
        # logging.info('open_qty_2')
        # logging.debug(open_qty_2)
        print('open_qty_2: ',open_qty_2)
        for j in filter_doc_locations:
            if open_qty_2 > 0:
                if item_code_2 == j['item_code']:
                    if open_qty_2 > j['qty']:
                        open_qty_2 = open_qty_2 - j['qty']
                        j['qty'] = j['qty']
                        j['stock_qty'] = j['qty']
                        my_picklist.append(j)
                        # logging.info('j In if')
                        # logging.debug(j)
                        # filter_doc_locations.remove(j)
                    else:
                        remain = open_qty_2
                        j['qty'] = remain
                        j['stock_qty'] = remain
                        open_qty_2 = 0
                        my_picklist.append(j)
                        # logging.info('j In else')
                        # logging.debug(j)
                        # filter_doc_locations.remove(j)
                    # logging.info('new_my_picklist')
                    # logging.debug(my_picklist)
            else:
                continue
    print('my_picklist: ',my_picklist)

    # logging.info('my_picklist')
    # logging.debug(my_picklist)

    return my_picklist
#------------------------------- /custome_picklist---------------------------------------------------

#------------------------------- custome_delivery_note ----------------------------------------------
@frappe.whitelist()
def custome_delivery_note(doc):
    doc = json.loads(doc)
    print('Doc: ',doc)

    parent_warehouse = doc['parent_warehouse']
    company = doc['company']

    items = doc.get('items')

    # seperating the brand transport_and_packing
    transport_and_packing_item = []
    for it in items:
        if 'brand' in it:
            if it['brand'] == 'Transport & Packing' or it['item_name'] == 'COURIER CHARGES 18%':
                # billed_amt = frappe.db.get_value('Sales Order Item',it['so_detail'],'billed_amt')
                # it['amount'] = it['amount'] - billed_amt
                transport_and_packing_item.append(it)

    def get_available_item_locations(item_code, from_warehouses, required_qty, company):
        # gets all items available in different warehouses
        warehouses = [x.get("name") for x in frappe.get_list("Warehouse", {"company": company,"parent_warehouse":from_warehouses}, "name")]

        filters = frappe._dict(
            {"item_code": item_code, "warehouse": ["in", warehouses], "actual_qty": [">", 0]}
        )

        item_locations = frappe.get_all(
            "Bin",
            fields=["warehouse", "actual_qty as qty"],
            filters=filters,
            limit=required_qty,
        )

        return item_locations

    # print('items: ',items)
    # from erpnext.stock.doctype.pick_list.pick_list import get_available_item_locations_for_other_item

    dc_filter_items = {}
    dc_filter_item_code = []
    dc_filter_doc_locations = []
    my_dc_list = []
    my_dc_list_2 = []

    # Return the actual_qty of item from warehouse
    def check_item_in_warehouse(parent_warehouse,item_code):
        actual_qty = frappe.db.sql(f"""
                                        SELECT item_code, SUM(actual_qty) as actual_qty
                                        FROM `tabBin`
                                        WHERE `tabBin`.warehouse
                                        IN (
                                            SELECT name FROM `tabWarehouse` WHERE
                                            `tabWarehouse`.parent_warehouse = '{parent_warehouse}'
                                            )
                                        AND `tabBin`.item_code = '{item_code}'
                                    """,as_dict=1)[0]
        return actual_qty

    for row in items:
        item_code = row['item_code']

        actual_qty_in_wh1 = check_item_in_warehouse(parent_warehouse,item_code)
        if actual_qty_in_wh1.item_code != None:
            actual_qty_in_wh = actual_qty_in_wh1.actual_qty
        else:
            actual_qty_in_wh = 0
        print('actual_qty_in_wh: ',actual_qty_in_wh)

        reserve = frappe.db.sql(f"""
                                    select item_code,sum(reserve_qty) as reserve_qty from `tabReservation Schedule Item` rsi
                                    join `tabReservation Schedule` rs
                                    on rs.name = rsi.parent
                                    where rsi.item_code = '{item_code}'
                                    and rs.parent_warehouse = '{parent_warehouse}'
                                    and (select status from `tabReservation Schedule` As rs WHERE rs.name = rsi.parent) = 'Open'
                                """,as_dict=1)[0]
        print('reserve: ',reserve)

        if reserve.item_code != None:
            reserve_qty = reserve.reserve_qty
        else:
            reserve_qty = 0
        print('reserve_qty: ',reserve_qty)

        open_qty = actual_qty_in_wh - reserve_qty
        print('open_qty: ',open_qty)

        if open_qty > 0 :
            if item_code not in dc_filter_items:
                dc_filter_items[item_code] = {'item_code': item_code, 'actual_qty_in_wh': actual_qty_in_wh, 'open_qty': open_qty}
                dc_filter_item_code.append(item_code)
            dc_filter_doc_locations.append(row)

    print('dc_filter_item_code: ',dc_filter_item_code)
    print('dc_filter_items: ',dc_filter_items)
    print('dc_filter_doc_locations: ',dc_filter_doc_locations)

    for i in dc_filter_item_code:
        item_code_2 = i
        temp = dc_filter_items.get(item_code_2)
        open_qty_2 = temp['open_qty']

        for j in dc_filter_doc_locations:
            if open_qty_2 > 0:
                if item_code_2 == j['item_code']:
                    if open_qty_2 > j['qty']:
                        open_qty_2 = open_qty_2 - j['qty']
                        j['qty'] = j['qty']
                        my_dc_list.append(j)
                        # dc_filter_doc_locations.remove(j)
                    else:
                        remain = open_qty_2
                        j['qty'] = remain
                        open_qty_2 = 0
                        my_dc_list.append(j)
                        # dc_filter_doc_locations.remove(j)
    print('my_dc_list: ',my_dc_list)

    def fetch_same_item_code(item_code):
        same_items = []
        for item_doc in my_dc_list:
            if item_code == item_doc['item_code']:
                same_items.append(item_doc)
        return same_items

    for item_code in dc_filter_item_code:
        item_bin_location = []
        bin_and_qty = {}
        from_warehouses = parent_warehouse
        required_qty = 0

        rows = fetch_same_item_code(item_code) # contain similer item_code
        locations = get_available_item_locations(item_code, from_warehouses, required_qty, company)
        print('locations: ',locations)
        for bin in locations:
            warehouse = bin['warehouse']
            qty = bin['qty']
            bin_and_qty[warehouse]=qty
        # print('bin_and_qty: ',bin_and_qty)

        for item_row in rows:
            row_qty = item_row['qty']
            if len(locations) > 0 :
                for loc in locations:
                    it2 = item_row.copy()
                    loc_wh = loc['warehouse']

                    if row_qty > 0 and bin_and_qty.get(loc_wh) != 0:
                        if row_qty > bin_and_qty.get(loc_wh):
                            it2['qty'] = bin_and_qty.get(loc_wh)
                            it2['warehouse'] = loc_wh
                            row_qty = row_qty - bin_and_qty.get(loc_wh)
                            bin_and_qty[loc_wh] = 0
                        else:
                            it2['qty'] = row_qty
                            it2['warehouse'] = loc_wh
                            bin_and_qty[loc_wh] = bin_and_qty.get(loc_wh) - row_qty
                            row_qty = 0
                        item_bin_location.append(it2)

        for k in item_bin_location:
            my_dc_list_2.append(k)

    for transport_packing in transport_and_packing_item:
        if len(transport_and_packing_item) != 0:
            my_dc_list_2.append(transport_packing)

    return my_dc_list_2
#------------------------------- /custome_delivery_note ----------------------------------------------


#-------------------------- Cancel Sales Order ---------------------------
#Report Name : Draft Sales Order ( Last 3 Month )

@frappe.whitelist()
def update_sales_order_status_to_cancel(**args):
    so_num = args.get('name')
    frappe.db.set_value('Sales Order',so_num,'status','Cancelled')
    frappe.db.set_value('Sales Order',so_num,'workflow_state','Cancelled')
    frappe.db.set_value('Sales Order',so_num,'docstatus','2')
 
    frappe.db.commit()

#----------------------------/ Cancel Sales Order on click ------------------
#