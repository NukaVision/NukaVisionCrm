# nukavisioncrm/doctype/contact_engagement/contact_engagement.py
import frappe
from frappe.model.document import Document
from nukavisioncrm.utils.logging import debug_probe
from nukavisioncrm.services.company import on_company_update
import logging

APP = "nukavisioncrm"  # app adın nvcrm ise "nvcrm" yap
TERMINALS = {"Go Offer", "Go End", "Go Stall"}
F_CE_STATE = "status_workflow"

class ContactEngagement(Document):
    def on_update(self):
        pass
        # # Sadece state değiştiyse çalış
        # if not self.has_value_changed(F_CE_STATE):
        #     return
        # state = (self.get(F_CE_STATE) or "").strip()
        # if state not in TERMINALS or not self.company or not self.contact:
        #     return

        # debug_probe(f"[CE:{self.name}] state → {state} (Company:{self.company}) (Contact:{self.contact})",logging.DEBUG)
        # doc = frappe.get_doc("Company", self.company)
        # frappe.enqueue(
        #         on_company_update,
        #         queue="short",
        #         enqueue_after_commit=True,
        #         doc=doc,
        #     )
        
        # debug_probe(f"[CE:{self.name}] scheduled Company Find Contact handler",logging.DEBUG)
