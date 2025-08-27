# nvcrm/services/company.py
import frappe
from frappe.utils import now_datetime, add_days
from frappe.model.workflow import apply_workflow
from nukavisioncrm.utils.logging import debug_probe
import logging



# ---- public hook ----
def on_company_update(doc, method=None):
    """Company Workflow 'update_field' = status_workflow olmalı.
    State değiştiğinde ilgili handler çalışır."""
    if not doc.has_value_changed("status_workflow"):
        return
    
    state = (doc.status_workflow or "").strip()
    HANDLERS = {
        "New Company": _handle_new_company,
        "Find Contact": _handle_find_contact,
        "Contact Found": _handle_contact_found,
        "Offer": _handle_offer,             # <--- yer hazır; içini sonra dolduracağız
        "Won": _handle_won,
        "Lost": _handle_lost,
        "Stalled": _handle_stalled,
    }
    handler = HANDLERS.get(state)
    if handler:
        handler(doc)


# ===================== HANDLERS =====================

def _handle_new_company(doc):
    """İlk kayıt anında yapılacaklar (placeholder)."""
    # ör: otomatik alan doldurma, not ekleme vs.
    pass


def _handle_find_contact(doc):
    """Find Contact'a girince: sıradaki kişiden bir Contact Engagement yarat.
    Child tablo: table_contact (Contact Link)."""
    # Zaten açık bir engagement varsa tekrar yaratma
    
    if doc.get("primary_contact"): # Test edilecek
        try:
            eng = frappe.get_doc("Contact Engagement", doc.primary_contact)
            if getattr(eng, "state", "") != "Go End":
                return
        except frappe.DoesNotExistError:
            pass

    
    # Child tabloyu doc üzerinden oku
    rows = list(doc.get("table_contact") or [])
    # skip işaretli olmayanları sırala (priority -> idx)
    rows = [r for r in rows if not (getattr(r, "skip", 0) or 0)]
    rows.sort(key=lambda r: ((getattr(r, "priority", None) or 1000), r.idx))



    if not rows:
        # Kişi yok → Stall’a çek (workflow aksiyonu after_commit’te)
        doc.db_set("retry_after", add_days(now_datetime(), 14), update_modified=False)

        def _stall_after_commit(name=doc.name):
            co = frappe.get_doc("Company", name)
            try:
                apply_workflow(co, "All Contact Tried")
            except Exception:
                co.db_set("status_workflow", "Stalled", update_modified=False)
        frappe.db.after_commit(_stall_after_commit)
        return

    chosen = rows[0]
    contact_name = chosen.contact

    
    # Engagement oluştur
    eng = frappe.new_doc("Contact Engagement")
    eng.company = doc.name
    eng.contact = contact_name
    eng.priority = getattr(chosen, "priority", None) or 1000
    eng.is_active = 1
    eng.insert(ignore_permissions=True)

    debug_probe(f"In Company: {doc.name}, Contact Engagement: {eng.name} created and set",logging.INFO)

    # Company üzerinde aktif/primary engagement’ı işaretle
    doc.db_set("primary_contact", eng.name, update_modified=False)


def _handle_contact_found(doc):
    """Engagement pozitif olduğunda Company Contact Found’da.
    Burada istersen otomatik Offer taslağı açmayı vb. yapabilirsin (şimdilik boş)."""
    pass


def _handle_offer(doc):
    """OFFER STATE – YER HAZIR
    Buraya: aktif teklifin senkronizasyonu, teklif oluşturma/yenileme,
    hatırlatıcı kurma vb. gelecektir. Şimdilik dokunmuyoruz."""
    pass


def _handle_won(doc):
    """Kazanıldı: kapanış işlemleri (placeholder)."""
    # ör: projeyi başlatma task'ları yaratma
    pass


def _handle_lost(doc):
    """Kaybedildi: analiz/kapanış (placeholder)."""
    # ör: lost_reason zorunlu kontrolü, rapor güncelleme
    pass


def _handle_stalled(doc):
    """Stalled: retry_after yoksa ata, primary_contact'ı temizleyebilirsin."""
    if not doc.get("retry_after"):
        doc.db_set("retry_after", add_days(now_datetime(), 14), update_modified=False)
    # İstersen:
    # doc.db_set("primary_contact", None, update_modified=False)


# ===================== (İsteğe bağlı) YARDIMCILAR =====================

def _apply_company_action_after_commit(company_name: str, action: str):
    """Aynı Company üzerinde workflow aksiyonu, re-entrancy riskine karşı after_commit."""
    def _run(name=company_name, act=action):
        co = frappe.get_doc("Company", name)
        apply_workflow(co, act)
    frappe.db.after_commit(_run)
