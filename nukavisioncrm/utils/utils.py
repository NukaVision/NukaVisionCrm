import frappe

try:
    from frappe.core.doctype.workflow_action.workflow_action import apply_workflow
except Exception:
    from frappe.model.workflow import apply_workflow

import logging

from nukavisioncrm.utils.logging import debug_probe



def ENQ(function, **kwargs):
    """Kısa enqueue (commit sonrası, short queue)."""
    return frappe.enqueue(
        function,
        queue="short",
        enqueue_after_commit=True,
        **kwargs
    )


def _apply_action(name: str, action: str = None, fallback_state: str = None, field: str = "status_workflow"):
    """Action varsa uygula, olmazsa state'i doğrudan yaz (aynı job context içinde)."""
    co = frappe.get_doc("Company", name)
    if action:
        try:
            apply_workflow(co, action)
            debug_probe(f"[{name}] action '{action}' applied")
            return
        except Exception as e:
            debug_probe(f"[{name}] action '{action}' failed: {e}", logging.ERROR)
    if fallback_state:
        co.db_set(field, fallback_state, update_modified=False)
        debug_probe(f"[{name}] state set → {fallback_state}")


def _apply_action_job(name: str, action: str = None, fallback_state: str = None):
    """Action’ı commit sonrası ayrı job’da uygula; fallback varsa state yaz."""
    debug_probe(f"[{name}] schedule action={action or '-'} fallback={fallback_state or '-'}")
    ENQ(
        _apply_action,
        name=name,
        action=action,
        fallback_state=fallback_state)
    

        
def _get_old_state(doc):
    """Doc save öncesi state'i al (yoksa None döner)."""
    try:
        return doc.get_doc_before_save().status_workflow
    except Exception:
        return None

    
