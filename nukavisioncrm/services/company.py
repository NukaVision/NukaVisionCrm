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
    """status_workflow değiştiğinde, commit'ten sonra job dispatch et."""
    if not doc.has_value_changed("status_workflow"):
        return

    company_name = doc.name
    new_state = (doc.status_workflow or "").strip()

    frappe.enqueue(
        f"{APP}.services.company._dispatch_company_state_job",
        queue="short",
        enqueue_after_commit=True,
        company_name=company_name,
        state=new_state
    )

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
        "Contact Found": _handle_contact_found,
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
    if doc.get("primary_contact"):
        try:
            eng = frappe.get_doc("Contact Engagement", doc.primary_contact)
            st = getattr(eng, "status_workflow", "") or getattr(eng, "state", "")
            if st not in ("Go End", "Go Offer", "Go Stall"):
                debug_probe(f"[Company:{doc.name}] [CE:{eng.name}] still active @ '{st}', skip")
                return
            if st == "Go Offer":
                _apply_company_action_job(doc.name, action="Mark Contact Found", fallback_state="Contact Found")
                debug_probe(f"[Company:{doc.name}] [CE:{eng.name}] → Contact Found", logging.INFO)
                return
            if st == "Go Stall":
                _apply_company_action_job(doc.name, action="All Contact Tried", fallback_state="Stalled")
                debug_probe(f"[Company:{doc.name}] [CE:{eng.name}] → Stalled", logging.INFO)
                return
            # st == "Go End" → yeni engagement yaratacağız
            debug_probe(f"[Company:{doc.name}] [CE:{eng.name}] finished @ '{st}', creating new...", logging.INFO)
        except frappe.DoesNotExistError:
            pass

    # 1) Sıradaki kişiyi seç
    chosen = _choose_contact(doc)
    if not chosen:
        debug_probe(f"[Company:{doc.name}] no contacts",logging.WARN)
        _go_stalled(doc)
        return

    # 1.5) Bu satırı bir daha seçmemek için skip=1 (parent'ı save etmeden)
    try:
        frappe.db.set_value(chosen.doctype, chosen.name, "skip", 1, update_modified=False)
    except Exception:
        pass

    # 2) Engagement oluştur
    eng = _create_engagement(doc.name, chosen.contact, priority=(getattr(chosen, "priority", None) or 1000))

    # 3) Aktif engagement’ı işaretle
    doc.db_set("primary_contact", eng.name, update_modified=False)
    debug_probe(f"[Company:{doc.name}] primary_contact → {eng.name}")

def _handle_contact_found(doc):
    debug_probe(f"[Company:{doc.name}] entered Contact Found")

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
    frappe.enqueue(
        f"{APP}.services.company._apply_company_action",
        queue="short",
        enqueue_after_commit=True,
        company_name=company_name,
        action=action,
        fallback_state=fallback_state
    )

def _create_engagement(company_name: str, contact_name: str, priority: int = 1000):
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
    return rows[0] if rows else None

def _go_stalled(doc):
    doc.db_set("retry_after", add_days(now_datetime(), 14), update_modified=False)
    _apply_company_action_job(doc.name, action="Stalled",fallback_state="Stalled")
