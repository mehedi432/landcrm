// Copyright (c) 2025, Abdullah Al Mehedi and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Tract Media", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Tract Profile", {
  // custom button or event on child table row
  onload: function (frm) {
    frm.fields_dict.land_tract.grid.add_custom_button('Add Media', function () {
      const selected = frm.fields_dict.land_tract.grid.get_selected();
      if (!selected || !selected.length) {
        frappe.msgprint("Please select a Land Tract row first.");
        return;
      }

      const row = selected[0];

      frappe.new_doc("Tract Media", {
        tract_row_id: row.name,
        tract_profile: frm.doc.name
      });
    });
  }
});

frappe.ui.form.on('Tract Media', {
  refresh: function (frm) {
    if (frm.doc.tract_profile) {
      frm.add_custom_button('Go Back to Tract Profile', () => {
        frappe.set_route('Form', 'Tract Profile', frm.doc.tract_profile);
      });
    } else {
      frm.add_custom_button('Go Back to List', () => {
        frappe.set_route('List', 'Tract Media');
      });
    }
  }
});


