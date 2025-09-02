import frappe
from .base import EmailProvider, SendResult
from typing import List, Dict, Optional

class FrappeSMTP(EmailProvider):
    name = "frappe_smtp"

    def send(self, to: List[str], subject: str, html: str,
             text: Optional[str] = None, from_email: Optional[str] = None,
             from_name: Optional[str] = None, headers: Optional[Dict[str, str]] = None,
             tags: Optional[List[str]] = None) -> SendResult:
        try:
            frappe.sendmail(
                recipients=to,
                subject=subject,
                message=html,
                delayed=False,
                reference_doctype=None,
                reference_name=None,
                sender=from_email,
                header=(),  # do not use header bar
                reply_to=None,
                with_container=False,
                attachments=None,
                content=text  # frappe çoğunlukla html'i kullanır; text fallback kalır
            )
            return SendResult(ok=True, provider=self.name, message_id=None)
        except Exception as e:
            return SendResult(ok=False, provider=self.name, error=str(e))
