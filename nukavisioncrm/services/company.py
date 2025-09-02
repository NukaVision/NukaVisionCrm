# nvcrm/services/company.py (veya nukavisioncrm/services/company.py)
import frappe
from frappe.utils import now_datetime, add_days


import nukavisioncrm.utils.utils as utils
import nukavisioncrm.utils.company_utils as company_utils
from nukavisioncrm.utils.logging import debug_probe

import logging

APP = "nukavisioncrm"  # <--- app adın nvcrm ise burayı "nvcrm" yap

# ---------------------- PUBLIC HOOK ----------------------
def on_company_update(doc, method=None):
    """commit'ten sonra job dispatch et."""
    debug_probe(f"[Company:{doc.name}] on_company_update fired", logging.DEBUG)

    company_name = doc.name
    new_state = (doc.status_workflow or "").strip()
    old_state = utils._get_old_state(doc)
   
    debug_probe(f"{new_state}", logging.INFO)
   # onceki state Offer ise yeni engagement yaratma
    if(new_state == "Find Contact"):
        if(old_state== "Offer"):
            # primary_contact'u temizle
            doc.db_set("primary_contact", None, update_modified=False)
            
        if(old_state == "Stalled"):
            debug_probe(f"[Company:{doc.name}] Back to the Find Contact", logging.INFO)
            # primary_contact'u temizle
            doc.db_set("primary_contact", None, update_modified=False)

            # retry_after'ı temizle
            doc.db_set("retry_after", None, update_modified=False)
            # butun contactlarin skiplerini 0 yap
            for r in doc.get("table_contact") or []:
                try:
                    frappe.db.set_value(r.doctype, r.name, "skip", 0, update_modified=False)
                except Exception:
                    frappe.throw("[Company:{doc.name}] Could not reset skip values of contacts")
                    
            debug_probe(f"[Company:{doc.name}] Contacts skip value is reseting", logging.INFO)



    utils.ENQ(
        _dispatch_company_state_job,
        company_name=company_name,
        state=new_state)

# ---------------------- JOB + DISPATCH ----------------------
def _dispatch_company_state_job(company_name: str, state: str):
    try:
        doc = frappe.get_doc("Company", company_name)
        debug_probe(f"[Company:{company_name}] JOB start → {state}")
        _dispatch_company_state(doc, state)
        debug_probe(f"[Company:{company_name}] JOB done → {state}")
    except Exception as e:
        debug_probe(f"[Company:{company_name}] JOB error: {e}")
        raise

def _dispatch_company_state(doc, state: str):
    HANDLERS = {
        "New Company": _handle_new_company,
        "Find Contact": _handle_find_contact,
        "Offer": _handle_offer,
        "Won": _handle_won,
        "Lost": _handle_lost,
        "Stalled": _handle_stalled,
    }
    handler = HANDLERS.get(state)
    if handler:
        debug_probe(f"[Company:{doc.name}] dispatch → {state}")
        handler(doc)

# ---------------------- HANDLERS ----------------------
def _handle_new_company(doc):
    debug_probe(f"[Company:{doc.name}] entered New Company")

def _handle_find_contact(doc):


    # 0) Var olan engagement terminal değilse yenisini yaratma
    try:
        if(not doc.primary_contact): # bos ise olustur
            debug_probe(f"[Company:{doc.name}] No primary contact, creating new...", logging.INFO)
            if company_utils._create(doc):
                debug_probe(f"[Company:{doc.name}] no contact left -> Stalled", logging.WARNING)
                doc.db_set("retry_after", add_days(now_datetime(), 14), update_modified=False)
                utils._apply_action_job(doc.name, action="Stalled",fallback_state="Stalled")
            else:
                return
        
        eng = frappe.get_doc("Contact Engagement", doc.primary_contact)
        st = getattr(eng, "status_workflow", "")

            
    except frappe.DoesNotExistError as e:
        debug_probe(f"[Company:{doc.name}] error : {e}", logging.WARNING)
        

    doc.reload()



def _handle_offer(doc):
    debug_probe(f"[Company:{doc.name}] entered Offer (placeholder)")

def _handle_won(doc):
    debug_probe(f"[Company:{doc.name}] entered Won")

def _handle_lost(doc):
    debug_probe(f"[Company:{doc.name}] entered Lost")

def _handle_stalled(doc):
    if not doc.get("retry_after"):
        doc.db_set("retry_after", add_days(now_datetime(), 14), update_modified=False)
    doc.db_set("primary_contact", None, update_modified=False)
    debug_probe(f"[Company:{doc.name}] entered Stalled; retry_after set")





