// Copyright (c) 2025, yunus ahmet akdal and contributors
// For license information, please see license.txt


frappe.ui.form.on("Company", {
	async refresh(frm) {
        
        // ContactStateMachine(frm);


	}
});

async function apply_workflow_action(frm,action)
{
    try {
        await frappe.xcall('frappe.model.workflow.apply_workflow', { doc: frm.doc, action });
        await frm.reload_doc();
        frappe.show_alert({ message: `Applied: ${action}`, indicator: 'green' });
    } catch (e) {
        frappe.msgprint({ title: __('Workflow failed'), message: e.message, indicator: 'red' });
        // Konsolda ayrıntı görmek için:
        // console.error(e);
    }
}



async function S1(frm) {

    frm.add_custom_button("Accept",()=> {
            // frm.doc.Actions
            frm.set_value("status","New Company");
            },"Contact Action");

    frm.add_custom_button("Decline",()=> {
            // frm.doc.Actions
            frm.set_value("status","New Company");
            },"Contact Action");            

};

async function S2(frm) {
};

async function S3(frm) {
  
};


async function S4(frm) {

    frm.add_custom_button("Accept",()=> {
        apply_workflow_action(frm, 'Contact Found'); 
        frappe.msgprint('Contact has found. Time to focus on offers..'); 
    },"Contact Action");
    
};


async function S5(frm) {

};


async function ContactStateMachine(frm)
{

    switch(frm.doc.contact_state_high) {
        case "No Answer (S1)":
            S1(frm);                     
        break;

        case "Negative (S2)":
            S2(frm);
        break;

        case "Unknown (S3)":
            S3(frm);
        break;

        case "Positive (S4)":
            S4(frm)
        break;

        case "Redirect (S5)":
            S5(frm)
        break;
        default:
        }
};
