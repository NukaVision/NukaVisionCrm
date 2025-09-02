import frappe
import nukavisioncrm.services.mail.state_machine as sm


STATE_FIELD = "mail_state"
ACTION_FIELD = "mail_action"
DT = "Contact Engagement"

@frappe.whitelist()
def allowed_actions(engagement_name: str, doctype: str = DT):
    state = frappe.db.get_value(doctype, engagement_name, STATE_FIELD)
    return sm._possible_events(state)

@frappe.whitelist()
def fire(engagement_name: str, action: str, doctype: str = DT):
    """Aksiyonu uygula (server-side yeniden doğrular)."""
    doc = frappe.get_doc(doctype, engagement_name)
    cur = doc.get(STATE_FIELD)

    # güvenlik: yalnızca izinli aksiyona izin ver
    allowed = set(sm._possible_events(cur))
    if action not in allowed:
        frappe.throw(f"Action '{action}' is not allowed from state '{cur}'")

    nxt = sm._run_state_machine(cur, action)
    if not nxt:
        frappe.throw("Transition not found")

    # doc.db_set(STATE_FIELD, nxt, update_modified=False)
    doc.db_set(ACTION_FIELD, action)
    doc.save()
    # burada on_enter vb. handler çağırmak istiyorsan ekle
    return {"from": cur, "to": nxt}

