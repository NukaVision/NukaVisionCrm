# nvcrm/services/company.py (veya nukavisioncrm/services/company.py)
import frappe
from frappe.utils import now_datetime, add_days

try:
    from frappe.core.doctype.workflow_action.workflow_action import apply_workflow
except Exception:
    from frappe.model.workflow import apply_workflow

from nukavisioncrm.utils.logging import debug_probe
import logging

APP = "nukavisioncrm"  # <--- app adın nvcrm ise burayı "nvcrm" yap

# ---------------------- PUBLIC HOOK ----------------------
def on_company_update(doc, method=None):
    """commit'ten sonra job dispatch et."""
    debug_probe(f"[Company:{doc.name}] on_company_update fired", logging.DEBUG)

    company_name = doc.name
    new_state = (doc.status_workflow or "").strip()
    old_state = _get_old_state(doc)
   
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



    ENQ(
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
            if _create(doc):
                debug_probe(f"[Company:{doc.name}] no contact left -> Stalled", logging.WARNING)
                doc.db_set("retry_after", add_days(now_datetime(), 14), update_modified=False)
                _apply_company_action_job(doc.name, action="Stalled",fallback_state="Stalled")
            else:
                return
        
        eng = frappe.get_doc("Contact Engagement", doc.primary_contact)
        st = getattr(eng, "status_workflow", "")
        if st == "Go Offer":
            debug_probe(f"[Company:{doc.name}] [CE:{eng.name}] → Contact Found", logging.WARNING)

            _apply_company_action_job(doc.name, action="Contact Found", fallback_state="Offer")
            
        elif st == "Go Stall":
            debug_probe(f"[Company:{doc.name}] [CE:{eng.name}] → Stalled", logging.WARNING)

            doc.db_set("retry_after", add_days(now_datetime(), 14), update_modified=False)
            _apply_company_action_job(doc.name, action="Stalled", fallback_state="Stalled")
            
        elif st == "Go End": # yeni engagement yaratacağız
            debug_probe(f"[Company:{doc.name}] [CE:{eng.name}] finished @ '{st}', creating new...", logging.INFO)

            if _create(doc):
                doc.db_set("retry_after", add_days(now_datetime(), 14), update_modified=False)
                _apply_company_action_job(doc.name, action="Stalled",fallback_state="Stalled") 
            
        else:
            debug_probe(f"[Company:{doc.name}] [CE:{eng.name}] still active @ '{st}', skipping...", logging.INFO)
            
    except frappe.DoesNotExistError:
        pass

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

# ---------------------- HELPERS ----------------------
def ENQ(function, **kwargs):
    """Kısa enqueue (commit sonrası, short queue)."""
    return frappe.enqueue(
        function,
        queue="short",
        enqueue_after_commit=True,
        **kwargs
    )

def _apply_company_action(company_name: str, action: str = None, fallback_state: str = None, field: str = "status_workflow"):
    """Action varsa uygula, olmazsa state'i doğrudan yaz (aynı job context içinde)."""
    co = frappe.get_doc("Company", company_name)
    if action:
        try:
            apply_workflow(co, action)
            debug_probe(f"[Company:{company_name}] action '{action}' applied")
            return
        except Exception as e:
            debug_probe(f"[Company:{company_name}] action '{action}' failed: {e}", logging.ERROR)
    if fallback_state:
        co.db_set(field, fallback_state, update_modified=False)
        debug_probe(f"[Company:{company_name}] state set → {fallback_state}")

def _apply_company_action_job(company_name: str, action: str = None, fallback_state: str = None):
    """Action’ı commit sonrası ayrı job’da uygula; fallback varsa state yaz."""
    debug_probe(f"[Company:{company_name}] schedule action={action or '-'} fallback={fallback_state or '-'}")
    ENQ(
        _apply_company_action,
        company_name=company_name,
        action=action,
        fallback_state=fallback_state)

def _create(doc):
    """Yeni engagement yarat ve Company’ye bağla."""
    chosen = _choose_contact(doc)
    if not chosen:
        return 1
    _create_engagement(doc, chosen)

    return 0

def _create_engagement(doc,chosen):
    """Yeni engagement yarat ve Company’ye bağla."""

    #Engagement oluştur
    eng = _create_engagement_doc(doc.name, chosen.contact, priority=(getattr(chosen, "priority", None) or 1000))

    #Aktif engagement’ı işaretle
    doc.db_set("primary_contact", eng.name, update_modified=False)
    debug_probe(f"[Company:{doc.name}] primary_contact → {eng.name}")
    

def _create_engagement_doc(company_name: str, contact_name: str, priority: int = 1000):
    eng = frappe.new_doc("Contact Engagement")
    eng.company = company_name
    eng.contact = contact_name
    eng.priority = priority
    eng.is_active = 1
    eng.insert(ignore_permissions=True)
    debug_probe(f"[Company:{company_name}] Engagement {eng.name} created for {contact_name}")
    return eng

def _choose_contact(doc):
    rows = list(doc.get("table_contact") or [])
    rows = [r for r in rows if not (getattr(r, "skip", 0) or 0)]
    rows.sort(key=lambda r: ((getattr(r, "priority", None) or 1000), r.idx))
    if not rows:
        debug_probe(f"[Company:{doc.name}] no contacts",logging.WARN)
        return None
    
    try:
        frappe.db.set_value(rows[0].doctype, rows[0].name, "skip", 1, update_modified=False)
    except Exception:
        pass
        
    return rows[0]

    
def _get_old_state(doc):
    """Doc save öncesi state'i al (yoksa None döner)."""
    try:
        return doc.get_doc_before_save().status_workflow
    except Exception:
        return None

    