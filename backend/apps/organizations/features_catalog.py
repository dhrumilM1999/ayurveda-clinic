"""
SAFE TO EDIT: the list of modules that can be switched on/off per branch (feature flags),
and the optional "additional features" switched on/off per organization.

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

# Additional (optional) features, switched on/off for the WHOLE organization (clinic group) by an
# organization admin in "Additional settings". Off by default: each clinic turns on only what it needs.
# - "group": heading on the settings screen
# - "requires": another additional feature that must be on for this one to work
# The basic pharmacy (dispense, stock by batch, purchases, suppliers, stock correction and history)
# is always there when the Pharmacy module is on; these switches only add extras to it.
ADDITIONAL_FEATURES = {
    "pharmacy_billing": {"group": "pharmacy", "label": "Pharmacy bills, payments and printing", "default": False},
    "pharmacy_discounts": {"group": "pharmacy", "label": "Discounts on pharmacy bills", "default": False,
                           "requires": "pharmacy_billing"},
    "pharmacy_sales_returns": {"group": "pharmacy", "label": "Sales returns (and credit notes)", "default": False},
    "pharmacy_loose_sale": {"group": "pharmacy", "label": "Sell loose (part of a pack)", "default": False},
    "pharmacy_racks": {"group": "pharmacy", "label": "Racks and shelf locations", "default": False},
    "pharmacy_barcode": {"group": "pharmacy", "label": "Barcodes and scanning", "default": False},
    "pharmacy_purchase_details": {"group": "pharmacy", "label": "Detailed purchase entry", "default": False},
    "pharmacy_opening_stock": {"group": "pharmacy", "label": "Opening stock entry", "default": False},
    "pharmacy_supplier_returns": {"group": "pharmacy", "label": "Returns to supplier", "default": False},
    "pharmacy_stock_alerts": {"group": "pharmacy", "label": "Stock alerts (low, out, expiry)", "default": False},
    "pharmacy_stock_ledger": {"group": "pharmacy", "label": "Stock ledger screen", "default": False},
    "pharmacy_stock_check": {"group": "pharmacy", "label": "Physical stock check", "default": False},
    "medicine_extra_details": {"group": "pharmacy", "label": "Extra product details", "default": False},
    # Billing
    "combined_opd_bill": {"group": "billing", "label": "Medicines on the OPD bill (one combined bill)",
                          "default": False, "requires": "pharmacy_billing"},
}
