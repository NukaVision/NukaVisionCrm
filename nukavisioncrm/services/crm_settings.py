from nukavisioncrm.services.mail.gateway import clear_provider_cache

def on_update(doc, method=None):
    clear_provider_cache()