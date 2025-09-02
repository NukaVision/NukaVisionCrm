import json
from frappe.utils import now_datetime
import frappe
from .gateway import send_email

DT = "NV Outbound Email"

def enqueue_mail(*, to: list[str], subject: str, html: str, text: str | None = None,
                 engagement: str | None = None, tags: list[str] | None = None, scheduled_at=None):
    doc = frappe.get_doc({
        "doctype": DT,
        "status": "Queued",
        "to_json": json.dumps(to),
        "subject": subject,
        "html": html,
        "text": text,
        "engagement": engagement,
        "tags_json": json.dumps(tags or []),
        "scheduled_at": scheduled_at or now_datetime()
    }).insert(ignore_permissions=True)
    return doc.name

def process_queue(limit: int = 50):
    rows = frappe.get_all(DT,
        filters={"status": "Queued", "scheduled_at": ["<=", now_datetime()]},
        fields=["name", "to_json", "subject", "html", "text", "engagement", "retry_count"], limit_page_length=limit)
    for r in rows:
        doc = frappe.get_doc(DT, r["name"])
        doc.db_set("status", "Sending", update_modified=False)
        res = send_email(to=json.loads(doc.to_json or "[]"),
                         subject=doc.subject, html=doc.html, text=doc.text,
                         tags=json.loads(doc.tags_json or "[]"))
        if res.ok:
            doc.db_set({"status": "Sent", "sent_at": now_datetime(),
                        "provider": res.provider, "provider_message_id": res.message_id}, update_modified=False)
        else:
            rc = (doc.retry_count or 0) + 1
            err = (res.error or "")[:1000]
            # basit backoff: 2,5,15 dk
            from frappe.utils import add_to_date
            delay_min = [2, 5, 15, 60][min(rc-1, 3)]
            doc.db_set({"status": "Queued", "retry_count": rc, "error": err,
                        "scheduled_at": add_to_date(now_datetime(), minutes=delay_min)}, update_modified=False)
