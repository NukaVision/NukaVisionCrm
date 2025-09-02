import frappe
import logging
from nukavisioncrm.utils.logging import debug_probe
from nukavisioncrm.services.mail.state_machine import _run_state_machine, _possible_events,INITIAL_STATE
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

APP = "nukavisioncrm"  # <--- app adın nvcrm ise burayı "nvcrm" yap

# ---------------------- PUBLIC HOOK ----------------------
def on_ce_update(doc, method=None):
    """commit'ten sonra job dispatch et."""
    debug_probe(f"[CE:{doc.name}] on_ce_update fired", logging.DEBUG)


    if not doc.mail_action:
        return
    
    if doc.mail_action not in _possible_events(doc.mail_state):
        debug_probe(f"[CE:{doc.name}] mail_action '{doc.mail_action}' not possible in state '{doc.mail_state}'", logging.WARNING)
        new_mail_state = INITIAL_STATE
        
    else:
        debug_probe(f"[CE:{doc.name}] mail_action '{doc.mail_action}' in state '{doc.mail_state}'", logging.INFO)
        new_mail_state = _run_state_machine(doc.mail_state,doc.mail_action)
        
    doc.db_set("mail_state",new_mail_state , update_modified=False)
    doc.db_set("mail_action",None , update_modified=False)