// Copyright (c) 2023, ajay patole and contributors
// For license information, please see license.txt

frappe.ui.form.on('Reservation Transfer Entry', {
	setup: function(frm) {
		frm.set_query("source_reservation_no", function() {
			return {
				filters: [
					['Reservation Schedule','docstatus','=',1],
					['Reservation Schedule','status','=','Open'],
				]
			}
		});
		frm.set_query("target_reservation_no", function() {
			return {
				filters: [
					['Reservation Schedule','docstatus','=',1],
					['Reservation Schedule','status','=','Open'],
				]
			}
		});
	},

	get_reserve_items : function(frm) {
	    let s_reservation_no = frm.doc.source_reservation_no;
		let t_reservation_no = frm.doc.target_information_section;
	    if (s_reservation_no){
            frappe.call({
                method: "reservation_system.reservation_system.doctype.reservation_transfer_entry.reservation_transfer_entry.get_items",
                args: {
                    s_res_no: cur_frm.doc.source_reservation_no,
					t_res_no: cur_frm.doc.target_reservation_no,
					s_par_wh: cur_frm.doc.s_parent_warehouse,
					t_par_wh: cur_frm.doc.t_parent_warehouse
                },
                callback : function(r) {
                    console.log(r);
                    console.log(r.message.length);
                    if (r.message){
						frm.doc.items = []

						$.each(r.message, function(_i, e){
							let entry = frm.add_child('items');
							entry.item_code = e.item_code;
							entry.qty = e.qty;
							entry.item_name = e.item_name;
							entry.description = e.description;
							entry.uom = e.uom;
							entry.rate = e.rate;
							entry.conversion_factor = e.conversion_factor;
							entry.reserve_qty = e.reserve_qty;
						})
						refresh_field('items')
                    }
                },
            });
	    }
    }
});
