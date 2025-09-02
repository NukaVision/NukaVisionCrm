import json, requests
from .base import EmailProvider, SendResult
from typing import List, Dict, Optional

class SendGridProvider(EmailProvider):
    name = "sendgrid"
    def __init__(self, api_key: str, tracking_domain: Optional[str] = None, ip_pool: Optional[str] = None):
        self.api_key = api_key
        self.tracking_domain = tracking_domain
        self.ip_pool = ip_pool

    def send(self, to: List[str], subject: str, html: str,
             text: Optional[str] = None, from_email: Optional[str] = None,
             from_name: Optional[str] = None, headers: Optional[Dict[str, str]] = None,
             tags: Optional[List[str]] = None) -> SendResult:
        data = {
            "personalizations": [{"to": [{"email": x} for x in to], "categories": tags or []}],
            "from": {"email": from_email or "no-reply@example.com", "name": from_name or "CRM"},
            "subject": subject,
            "content": [{"type": "text/html", "value": html}],
        }
        if text:
            data["content"].append({"type": "text/plain", "value": text})
        if self.tracking_domain:
            data["tracking_settings"] = {"click_tracking": {"enable": True}, "ganalytics": {"enable": False}}
        if self.ip_pool:
            data["ip_pool_name"] = self.ip_pool
        if headers:
            data["headers"] = headers

        try:
            r = requests.post("https://api.sendgrid.com/v3/mail/send",
                              headers={"Authorization": f"Bearer {self.api_key}",
                                       "Content-Type": "application/json"},
                              data=json.dumps(data), timeout=10)
            if r.status_code in (200, 202):
                # Message-Id özel header’ı olmayabilir; SendGrid 202 Accepted döner
                return SendResult(ok=True, provider=self.name, message_id=r.headers.get("X-Message-Id"), raw={"status": r.status_code})
            return SendResult(ok=False, provider=self.name, error=f"{r.status_code} {r.text}")
        except Exception as e:
            return SendResult(ok=False, provider=self.name, error=str(e))
