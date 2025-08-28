import frappe
import logging
from functools import lru_cache

@lru_cache
def get_log():
    # level parametresi YOK; sadece allow_site / rotation parametreleri ver
    log = frappe.logger(
        "nvcrm",
        allow_site=True,     # site'e özel: sites/<site>/logs/nvcrm.log
        file_count=10,
        max_size=10_000_000
    )
    # Seviyeleri Python logging ile ayarla
    
    for h in getattr(log, "handlers", []):
        try:
            h.setLevel(logging.DEBUG)
        except Exception:
            pass
    return log

def debug_probe(msg: str,level: int=logging.DEBUG):
    log = get_log()
    log.setLevel(level)

    log.log(level,f"[PROBE] {msg}")
