"""
SAFE TO EDIT: the list of modules that can be switched on/off per branch (feature flags).

- "label" is shown in English if no translation exists (screen text is in frontend/src/i18n).
- "default" is used when a branch has never changed the switch.
To add a new switch, add one line here. No database change is needed.
"""

FEATURES = {
    "appointments": {"label": "Appointments and queue", "default": True},
    "panchakarma": {"label": "Panchakarma and therapy", "default": False},
    "pharmacy": {"label": "Pharmacy and stock", "default": True},
    "diet": {"label": "Diet and lifestyle charts", "default": False},
    "whatsapp_share": {"label": "Share by WhatsApp", "default": True},
    "ai_scribe": {"label": "AI scribe (voice to case sheet)", "default": False},
    "ai_summary": {"label": "AI patient summary", "default": False},
}
