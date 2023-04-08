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

	    if (so_number){
	        frappe.call({
	            method:'reservation_system.reservation_system.doctype.reservation_schedule.reservation_schedule.get_items',
	            args:{
					so_number:so_number,
				}
	        }).done((r) => {

	           frm.doc.items = []
	           
	           $.each(r.message, function(_i, e){
				console.log(e)
				let entry = frm.add_child('items');
	               entry.item_code = e.item_code;
	               entry.item_name = e.item_name;
	               entry.qty = e.qty;
                   entry.actual_qty = e.actual_qty;
				   entry.description = e.description;
				   entry.uom = e.uom;
				   entry.rate = e.rate;
				   entry.conversion_factor = e.conversion_factor;
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
	               entry.qty = e.qty;
                   entry.actual_qty = e.actual_qty;
				   entry.description = e.description;
				   entry.uom = e.uom;
				   entry.rate = e.rate;
				   entry.conversion_factor = e.conversion_factor;
	           })
	           refresh_field('items')
	        })
	    }
    },
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



