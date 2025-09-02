import frappe

import logging
from nukavisioncrm.utils.logging import debug_probe

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