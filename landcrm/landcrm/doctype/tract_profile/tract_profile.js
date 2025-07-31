// Copyright (c) 2025, Abdullah Al Mehedi and contributors
// For license information, please see license.txt


frappe.ui.form.on('Tract Profile', {
  refresh(frm) {
      // Add a custom button to trigger extraction
      frm.add_custom_button('Extract Tract Data', () => {
          frappe.call({
              method: "extract_and_save_tract_data",
              doc: frm.doc,
              freeze: true,
              freeze_message: "Extracting tract data from map...",
              callback: function(r) {
                  if (!r.exc) {
                      frappe.msgprint('Tract data extracted successfully!');
                      frm.reload_doc(); // reload to see updated child table
                      console.log("Extracted data:", r.message);
                  }
              }
          });
      });
  },
});

frappe.ui.form.on('Land Tract', {
  open_tract_media: function (frm, cdt, cdn) {
      let row = locals[cdt][cdn];

      // Open new Tract Media doc with prefilled values
      frappe.new_doc('Tract Media', {
          tract_id: row.tract_id,
          tract_name: row.tract_name,
          tract_profile: frm.doc.name  // Optional: add reverse link to Tract Profile
      });
  }
});


  