import frappe
from typing import List, Optional, Dict
from types import SimpleNamespace

from .providers.base import EmailProvider, SendResult
from .providers.frappe_smtp import FrappeSMTP
from .providers.sendgrid import SendGridProvider

PROVIDERS_CACHE: Dict[str, EmailProvider] = {}

def _load_settings():
    # CRM Settings (Singleton) – alanlar:
    # provider, api_key, from_email, from_name, tracking_domain, ip_pool,
    # backup_provider, backup_api_key, rate_per_minute
    return frappe.get_single("CRM Settings")

# --- provider factory (tek noktadan geçsin) ------------------------------------
def _build_from_settings(s) -> EmailProvider:
    """Primary için cache'lenen provider'ı üretir."""
    if s.provider == "sendgrid":
        return SendGridProvider(
            api_key=getattr(s, "api_key", None),
            tracking_domain=getattr(s, "tracking_domain", None),
            ip_pool=getattr(s, "ip_pool", None),
        )
    # Diğer sağlayıcılar eklenebilir...
    return FrappeSMTP()

def _build_ephemeral(provider_name: str, api_key: Optional[str] = None,
                     tracking_domain: Optional[str] = None,
                     ip_pool: Optional[str] = None) -> EmailProvider:
    """Fallback gibi tek seferlik durumlar için cache'siz adapter."""
    if provider_name == "sendgrid":
        return SendGridProvider(api_key=api_key, tracking_domain=tracking_domain, ip_pool=ip_pool)
    return FrappeSMTP()

def get_provider(settings=None) -> EmailProvider:
    """Primary provider – cache'li."""
    s = settings or _load_settings()
    key = (s.provider or "frappe_smtp")
    if key not in PROVIDERS_CACHE:
        PROVIDERS_CACHE[key] = _build_from_settings(s)
    return PROVIDERS_CACHE[key]

def clear_provider_cache():
    """Settings güncellendiğinde çağır: cache'i temizler."""
    PROVIDERS_CACHE.clear()

# --- public API ----------------------------------------------------------------
def send_email(to: List[str], subject: str, html: str,
               text: Optional[str] = None,
               headers: Optional[Dict[str, str]] = None,
               tags: Optional[List[str]] = None,
               from_email: Optional[str] = None,
               from_name: Optional[str] = None) -> SendResult:
    # List-Unsubscribe header (deliverability)
    headers = headers or {}
    if "List-Unsubscribe" not in headers:
        headers["List-Unsubscribe"] = "<mailto:unsubscribe@example.com>, <https://example.com/unsub?id=...>"

    s = _load_settings()

    # 1) Primary
    provider = get_provider(s)
    res = provider.send(
        to=to, subject=subject, html=html, text=text,
        headers=headers, tags=tags or ["crm"],
        from_email=from_email or getattr(s, "from_email", None),
        from_name=from_name or getattr(s, "from_name", None),
    )
    if res.ok:
        return res

    # 2) Fallback (cache'siz, settings'i mutate ETME)
    backup_name = getattr(s, "backup_provider", None)
    backup_key  = getattr(s, "backup_api_key", None)
    
    if backup_name and backup_key:
        backup = _build_ephemeral(
            provider_name=backup_name,
            api_key=backup_key,
            tracking_domain=getattr(s, "tracking_domain", None),
            ip_pool=getattr(s, "ip_pool", None),
        )
        res2 = backup.send(
            to=to, subject=subject, html=html, text=text,
            headers=headers, tags=tags or ["crm"],
            from_email=from_email or getattr(s, "from_email", None),
            from_name=from_name or getattr(s, "from_name", None),
        )
        return res2

    return res
