// Copyright (c) 2022, ajay patole and contributors
// For license information, please see license.txt

frappe.ui.form.on('Reservation Schedule', {
	setup: function(frm) {
		frm.set_query("so_number", function() {
			return {
				filters: [
					['Sales Order','docstatus','=',1],
					['Sales Order','customer','=',cur_frm.doc.customer],
					['Sales Order','status','=','To Deliver and Bill'],
				]
			}
		});

		frm.set_query("quotation", function() {
			return {
				filters: [
					['Quotation', 'docstatus','=',1],
					['Quotation','party_name','=',cur_frm.doc.customer],
					['Quotation','status','=','Open'],
				]
			}
		});

		frm.set_query('parent_warehouse', function() {
			return {
				filters: [
					['Warehouse','is_group','=',1],
				]
			}
		});
	}
});

// Script to populate the items when we select so_number or quotation
frappe.ui.form.on('Reservation Schedule', {
    so_number: function(frm) {
	    let so_number = frm.doc.so_number;
	    console.log(frm);
	    if (so_number){
	        frappe.call({
	            method:'reservation_system.reservation_system.doctype.reservation_schedule.reservation_schedule.get_items',
	            args:{
					so_number:so_number,
				}
	        }).done((r) => {

	           frm.doc.items = []
	           $.each(r.message, function(_i, e){
				let entry = frm.add_child('items');
					entry.item_code = e.item_code;
					entry.item_name = e.item_name;
					entry.description = e.description;
					entry.item_group = e.item_group;
					entry.brand = e.brand;
					entry.image = e.image;
					entry.qty = e.qty;
					entry.stock_uom = e.stock_uom;
					entry.uom = e.uom;
					entry.conversion_factor = e.conversion_factor;
					entry.stock_qty = e.stock_qty;
					entry.price_list_rate = e.price_list_rate;
					entry.base_price_list_rate = e.base_price_list_rate;
					entry.margin_type = e.margin_type;
					entry.margin_rate_or_amount = e.margin_rate_or_amount;
					entry.rate_with_margin = e.rate_with_margin;
					entry.discount_percentage = e.discount_percentage;
					entry.discount_amount = e.discount_amount;
					entry.base_rate_with_margin = e.base_rate_with_margin;
					entry.rate = e.rate;
					entry.amount = e.amount;
					entry.item_tax_template = e.item_tax_template;
					entry.base_rate = e.base_rate;
					entry.base_amount = e.base_amount;
					entry.pricing_rules = e.pricing_rules;
					entry.stock_uom_rate = e.stock_uom_rate;
					entry.is_free_item = e.is_free_item;
					entry.grant_commission = e.grant_commission;
					entry.net_rate = e.net_rate;
					entry.net_amount = e.net_amount;
					entry.base_net_rate = e.base_net_rate;
					entry.base_net_amount = e.base_net_amount;
					entry.billed_amt = e.billed_amt;
					entry.valuation_rate = e.valuation_rate;
					entry.gross_profit = e.gross_profit;
					entry.delivered_by_supplier = e.delivered_by_supplier;
					entry.supplier = e.supplier;
					entry.weight_per_unit = e.weight_per_unit;
					entry.total_weight = e.total_weight;
					entry.weight_uom = e.weight_uom;
					entry.warehouse = e.warehouse;
					entry.target_warehouse = e.target_warehouse;
					entry.prevdoc_docname = e.prevdoc_docname;
					entry.quotation_item = e.quotation_item;
					entry.against_blanket_order = e.against_blanket_order;
					entry.blanket_order = e.blanket_order;
					entry.blanket_order_rate = e.blanket_order_rate;
					entry.bom_no = e.bom_no;
					entry.projected_qty = e.projected_qty;
					entry.actual_qty = e.actual_qty;
					entry.ordered_qty = e.ordered_qty;
					entry.planned_qty = e.planned_qty;
					entry.work_order_qty = e.work_order_qty;
					entry.delivered_qty = e.delivered_qty;
					entry.produced_qty = e.produced_qty;
					entry.returned_qty = e.returned_qty;
					entry.picked_qty = e.picked_qty;
					entry.additional_notes = e.additional_notes;
					entry.material_request_item = e.material_request_item;
					entry.purchase_order_item = e.purchase_order_item;
					entry.so_item_name = e.name;
	           })
	           refresh_field('items')
	        })
	    }
    },

	quotation: function(frm) {
	    let quotation = frm.doc.quotation;
	    
	    if (quotation){
	        frappe.call({
	            method:'reservation_system.reservation_system.doctype.reservation_schedule.reservation_schedule.get_items',
	            args:{
					quotation:quotation,
				}
	        }).done((r) => {
				
	           frm.doc.items = []
			   
	           $.each(r.message, function(_i, e){
	               let entry = frm.add_child('items');
						entry.item_code = e.item_code;
						entry.item_name = e.item_name;
						entry.description = e.description;
						entry.item_group = e.item_group;
						entry.brand = e.brand;
						entry.image = e.image;
						entry.qty = e.qty;
						entry.stock_uom = e.stock_uom;
						entry.uom = e.uom;
						entry.conversion_factor = e.conversion_factor;
						entry.stock_qty = e.stock_qty;
						entry.price_list_rate = e.price_list_rate;
						entry.base_price_list_rate = e.base_price_list_rate;
						entry.margin_type = e.margin_type;
						entry.margin_rate_or_amount = e.margin_rate_or_amount;
						entry.rate_with_margin = e.rate_with_margin;
						entry.discount_percentage = e.discount_percentage;
						entry.discount_amount = e.discount_amount;
						entry.base_rate_with_margin = e.base_rate_with_margin;
						entry.rate = e.rate;
						entry.amount = e.amount;
						entry.item_tax_template = e.item_tax_template;
						entry.base_rate = e.base_rate;
						entry.base_amount = e.base_amount;
						entry.pricing_rules = e.pricing_rules;
						entry.stock_uom_rate = e.stock_uom_rate;
						entry.is_free_item = e.is_free_item;
						entry.grant_commission = e.grant_commission;
						entry.net_rate = e.net_rate;
						entry.net_amount = e.net_amount;
						entry.base_net_rate = e.base_net_rate;
						entry.base_net_amount = e.base_net_amount;
						entry.billed_amt = e.billed_amt;
						entry.valuation_rate = e.valuation_rate;
						entry.gross_profit = e.gross_profit;
						entry.delivered_by_supplier = e.delivered_by_supplier;
						entry.supplier = e.supplier;
						entry.weight_per_unit = e.weight_per_unit;
						entry.total_weight = e.total_weight;
						entry.weight_uom = e.weight_uom;
						entry.warehouse = e.warehouse;
						entry.target_warehouse = e.target_warehouse;
						entry.prevdoc_docname = e.prevdoc_docname;
						entry.quotation_item = e.quotation_item;
						entry.against_blanket_order = e.against_blanket_order;
						entry.blanket_order = e.blanket_order;
						entry.blanket_order_rate = e.blanket_order_rate;
						entry.bom_no = e.bom_no;
						entry.projected_qty = e.projected_qty;
						entry.actual_qty = e.actual_qty;
						entry.ordered_qty = e.ordered_qty;
						entry.planned_qty = e.planned_qty;
						entry.work_order_qty = e.work_order_qty;
						entry.delivered_qty = e.delivered_qty;
						entry.produced_qty = e.produced_qty;
						entry.returned_qty = e.returned_qty;
						entry.picked_qty = e.picked_qty;
						entry.additional_notes = e.additional_notes;
						entry.material_request_item = e.material_request_item;
						entry.purchase_order_item = e.purchase_order_item;
						entry.so_item_name = e.name;
	           })
	           refresh_field('items')
	        })
	    }
    },

	// while selecting parent_warehouse it will populate items(neglecting the item whose delivery is done)
	parent_warehouse: function(frm){
		let so_number = frm.doc.so_number;
	    if (so_number){
	        frappe.call({
	            method:'reservation_system.reservation_system.doctype.reservation_schedule.reservation_schedule.get_items',
	            args:{
					so_number:so_number,
				}
	        }).done((r) => {

	           frm.doc.items = []
	           $.each(r.message, function(_i, e){
				let entry = frm.add_child('items');
					entry.item_code = e.item_code;
					entry.item_name = e.item_name;
					entry.description = e.description;
					entry.item_group = e.item_group;
					entry.brand = e.brand;
					entry.image = e.image;
					entry.qty = e.qty;
					entry.stock_uom = e.stock_uom;
					entry.uom = e.uom;
					entry.conversion_factor = e.conversion_factor;
					entry.stock_qty = e.stock_qty;
					entry.price_list_rate = e.price_list_rate;
					entry.base_price_list_rate = e.base_price_list_rate;
					entry.margin_type = e.margin_type;
					entry.margin_rate_or_amount = e.margin_rate_or_amount;
					entry.rate_with_margin = e.rate_with_margin;
					entry.discount_percentage = e.discount_percentage;
					entry.discount_amount = e.discount_amount;
					entry.base_rate_with_margin = e.base_rate_with_margin;
					entry.rate = e.rate;
					entry.amount = e.amount;
					entry.item_tax_template = e.item_tax_template;
					entry.base_rate = e.base_rate;
					entry.base_amount = e.base_amount;
					entry.pricing_rules = e.pricing_rules;
					entry.stock_uom_rate = e.stock_uom_rate;
					entry.is_free_item = e.is_free_item;
					entry.grant_commission = e.grant_commission;
					entry.net_rate = e.net_rate;
					entry.net_amount = e.net_amount;
					entry.base_net_rate = e.base_net_rate;
					entry.base_net_amount = e.base_net_amount;
					entry.billed_amt = e.billed_amt;
					entry.valuation_rate = e.valuation_rate;
					entry.gross_profit = e.gross_profit;
					entry.delivered_by_supplier = e.delivered_by_supplier;
					entry.supplier = e.supplier;
					entry.weight_per_unit = e.weight_per_unit;
					entry.total_weight = e.total_weight;
					entry.weight_uom = e.weight_uom;
					entry.warehouse = e.warehouse;
					entry.target_warehouse = e.target_warehouse;
					entry.prevdoc_docname = e.prevdoc_docname;
					entry.quotation_item = e.quotation_item;
					entry.against_blanket_order = e.against_blanket_order;
					entry.blanket_order = e.blanket_order;
					entry.blanket_order_rate = e.blanket_order_rate;
					entry.bom_no = e.bom_no;
					entry.projected_qty = e.projected_qty;
					entry.actual_qty = e.actual_qty;
					entry.ordered_qty = e.ordered_qty;
					entry.planned_qty = e.planned_qty;
					entry.work_order_qty = e.work_order_qty;
					entry.delivered_qty = e.delivered_qty;
					entry.produced_qty = e.produced_qty;
					entry.returned_qty = e.returned_qty;
					entry.picked_qty = e.picked_qty;
					entry.additional_notes = e.additional_notes;
					entry.material_request_item = e.material_request_item;
					entry.purchase_order_item = e.purchase_order_item;
					entry.so_item_name = e.name;
	           })
	           refresh_field('items')
	        })
	    }
	}
});

//button 
frappe.ui.form.on('Reservation Schedule', {
	refresh: function(frm) {
		//create delivery note and pick list
		if (frm.doc.docstatus == 1 && frm.doc.status != 'Complete' && frm.doc.status != 'Draft' && frm.doc.status != 'Hold' && frm.doc.status != 'Close') {
			frm.add_custom_button(__('Pick List'), () => make_pick_list(), __('Create'));
			frm.add_custom_button(__('Delivery Note'), () => make_delivery_note(), __('Create'));
			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		// Status Button (Hold and Close)
		if (frm.doc.docstatus == 1 && frm.doc.status != 'Complete' && frm.doc.status != 'Draft' && frm.doc.status != 'Hold' && frm.doc.status != 'Close') {
			frm.add_custom_button(__('Hold'), () => change_status_to_hold(), __('Status'));
			frm.add_custom_button(__('Close'), () => change_status_to_close(), __('Status'));
		}
		if (frm.doc.status == 'Hold'){
			frm.add_custom_button(__('Reopen'), () => reopen_hold_doc());
		}
		if (frm.doc.status == 'Close'){
			frm.add_custom_button(__('Reopen'), () => reopen_close_doc());
		}

		// To Enable Download Button
		cur_frm.get_field("items").grid.setup_download()
	},
	setup_download() {
		let title = this.df.label || frappe.model.unscrub(this.df.fieldname);
		$(this.wrapper)
			.find(".grid-download")
			.removeClass("hidden")
			.on("click", () => {
				var data = [];
				var docfields = [];
				data.push([__("Bulk Edit {0}", [title])]);
				data.push([]);
				data.push([]);
				data.push([]);
				data.push([__("The CSV format is case sensitive")]);
				data.push([__("Do not edit headers which are preset in the template")]);
				data.push(["------"]);
				$.each(frappe.get_meta(this.df.options).fields, (i, df) => {
					// don't include the read-only field in the template
					if (frappe.model.is_value_type(df.fieldtype)) {
						data[1].push(df.label);
						data[2].push(df.fieldname);
						let description = (df.description || "") + " ";
						if (df.fieldtype === "Date") {
							description += frappe.boot.sysdefaults.date_format;
						}
						data[3].push(description);
						docfields.push(df);
					}
				});

				// add data
				$.each(this.frm.doc[this.df.fieldname] || [], (i, d) => {
					var row = [];
					$.each(data[2], (i, fieldname) => {
						var value = d[fieldname];

						// format date
						if (docfields[i].fieldtype === "Date" && value) {
							value = frappe.datetime.str_to_user(value);
						}

						row.push(value || "");
					});
					data.push(row);
				});

				frappe.tools.downloadify(data, null, title);
				return false;
			});
	}
});

// Create Delivery Note button
function make_delivery_note() {
	frappe.model.open_mapped_doc({
		method: "reservation_system.reservation_system.doctype.reservation_schedule.reservation_schedule.make_delivery_note",
		frm: cur_frm
	})
}

// Create Pick List Button
function make_pick_list() {
	frappe.model.open_mapped_doc({
		method: "reservation_system.reservation_system.doctype.reservation_schedule.reservation_schedule.make_pick_list",
		frm: cur_frm
	})
}

// Hold Button
function change_status_to_hold() {
	frappe.call({
		method:"reservation_system.reservation_system.doctype.reservation_schedule.reservation_schedule.change_status_to_hold",
		args: {
			"source_name": cur_frm.doc.name,
		},
		callback : function(r) {
			cur_frm.reload_doc();
		},
	})
}

// Close Button
function change_status_to_close() {
	frappe.call({
		method:"reservation_system.reservation_system.doctype.reservation_schedule.reservation_schedule.change_status_to_close",
		args: {
			"source_name": cur_frm.doc.name,
		},
		callback : function(r) {
			cur_frm.reload_doc();
		},
	})
}

// Button - Reopen Close doc
function reopen_hold_doc() {
	frappe.call({
		method:"reservation_system.reservation_system.doctype.reservation_schedule.reservation_schedule.reopen_hold_doc",
		args: {
			"source_name": cur_frm.doc.name,
			"parent_warehouse": cur_frm.doc.parent_warehouse,
		},
		callback : function(r) {
			cur_frm.reload_doc();
		},
	})
}

// Button - Reopen Hold doc	
function reopen_close_doc() {
	frappe.call({
		method:"reservation_system.reservation_system.doctype.reservation_schedule.reservation_schedule.reopen_close_doc",
		args: {
			"source_name": cur_frm.doc.name,
			"parent_warehouse": cur_frm.doc.parent_warehouse,
		},
		callback : function(r) {
			cur_frm.reload_doc();
		},
	})
}



