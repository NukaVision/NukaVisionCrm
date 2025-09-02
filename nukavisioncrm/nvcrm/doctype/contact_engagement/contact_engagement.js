// Copyright (c) 2025, yunus ahmet akdal and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Contact Engagement", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Contact Engagement", {
  refresh(frm) {
    if (!frm.doc.name) return;
    // önce grubu temizle (yeniden yüklenince çift buton olmasın)
    frm.clear_custom_buttons();
    frappe.call("nukavisioncrm.services.mail.state_machine_wrapper.allowed_actions", {
      engagement_name: frm.doc.name
    }).then(r => {
      const actions = r.message || [];
      if (!actions.length) return;
      actions.forEach(action => {
        frm.add_custom_button(action, () => runAction(frm, action), "Engagement");
      });
    });
  }
});

function runAction(frm, action) {
  frappe.call("nukavisioncrm.services.mail.state_machine_wrapper.fire", {
    engagement_name: frm.doc.name,
    action
  }).then(r => {
    const res = r.message || {};
    frappe.show_alert({
      message: `State: ${res.from} → ${res.to} (${action})`,
      indicator: "green"
    });
    frm.reload_doc(); // state değişti; buton seti de yenilensin
  }).catch(() => {
    frappe.msgprint(__("This action is not allowed right now."));
  });
}