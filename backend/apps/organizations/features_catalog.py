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
# organization admin in "Additional settings". Extras are off by default ("default": False) so each clinic
# turns on only what it needs; the stock basics are on by default because the pharmacy always worked that way.
# - "group": heading on the settings screen
# - "requires": another additional feature that must be on for this one to work
# The basic pharmacy (dispense, stock by batch, purchases, suppliers, stock correction and history)
# is always there when the Pharmacy module is on; these switches only add extras to it.
ADDITIONAL_FEATURES = {
    # Medicine stock basics - ON by default (this is how the pharmacy has always worked); switch off what you
    # do not use. Stock tracking itself is the "Pharmacy and stock" module (Settings -> Modules).
    "pharmacy_batch_tracking": {"group": "stock", "label": "Batch tracking", "default": True},
    "pharmacy_expiry_tracking": {"group": "stock", "label": "Expiry tracking", "default": True},
    "pharmacy_purchase_price": {"group": "stock", "label": "Purchase price", "default": True},
    "pharmacy_selling_price": {"group": "stock", "label": "Selling price / MRP", "default": True},
    "pharmacy_suppliers": {"group": "stock", "label": "Supplier management", "default": True},
    "pharmacy_billing": {"group": "pharmacy", "label": "Pharmacy bills, payments and printing", "default": False,
                         "requires": "pharmacy_selling_price"},
    "pharmacy_discounts": {"group": "pharmacy", "label": "Discounts on pharmacy bills", "default": False,
                           "requires": "pharmacy_billing"},
    "pharmacy_sales_returns": {"group": "pharmacy", "label": "Sales returns (and credit notes)", "default": False},
    "pharmacy_loose_sale": {"group": "pharmacy", "label": "Sell loose (part of a pack)", "default": False},
    "pharmacy_racks": {"group": "pharmacy", "label": "Racks and shelf locations", "default": False},
    "pharmacy_barcode": {"group": "pharmacy", "label": "Barcodes and scanning", "default": False},
    "pharmacy_purchase_details": {"group": "pharmacy", "label": "Detailed purchase entry", "default": False,
                                  "requires": "pharmacy_purchase_price"},
    "pharmacy_opening_stock": {"group": "pharmacy", "label": "Opening stock entry", "default": False},
    "pharmacy_supplier_returns": {"group": "pharmacy", "label": "Returns to supplier", "default": False},
    "pharmacy_stock_alerts": {"group": "pharmacy", "label": "Stock alerts (low, out, expiry)", "default": False},
    "pharmacy_stock_ledger": {"group": "pharmacy", "label": "Stock ledger screen", "default": False},
    "pharmacy_stock_check": {"group": "pharmacy", "label": "Physical stock check", "default": False},
    "medicine_extra_details": {"group": "pharmacy", "label": "Extra product details", "default": False},
    "pharmacy_counter_sale": {"group": "pharmacy", "label": "Counter sale (without a prescription)", "default": False,
                              "requires": "pharmacy_billing"},
    # Pharmacy stock labels: stuck on the packs on the shelf. Medicine, pack, MRP, GST, batch, expiry and a barcode;
    # no patient details. Scanning the barcode at billing adds that exact batch.
    "pharmacy_stock_labels": {"group": "stock_labels", "label": "Pharmacy stock labels (barcode)", "default": False,
                              "requires": "pharmacy_barcode"},
    # Patient medicine labels (dose labels for medicines given to a patient). Medicine name, dosage, days and
    # instructions are always printed; these switches add the optional fields.
    "medicine_labels": {"group": "labels", "label": "Patient medicine labels", "default": False},
    "label_patient": {"group": "labels", "label": "Label: patient name", "default": True, "requires": "medicine_labels"},
    "label_quantity": {"group": "labels", "label": "Label: quantity", "default": True, "requires": "medicine_labels"},
    "label_times": {"group": "labels", "label": "Label: morning / noon / night boxes", "default": True,
                    "requires": "medicine_labels"},
    "label_expiry": {"group": "labels", "label": "Label: expiry date", "default": True, "requires": "medicine_labels"},
    "label_batch": {"group": "labels", "label": "Label: batch number", "default": False, "requires": "medicine_labels"},
    "label_price": {"group": "labels", "label": "Label: MRP / price", "default": False, "requires": "medicine_labels"},
    "label_code": {"group": "labels", "label": "Label: QR code", "default": False, "requires": "medicine_labels"},
    "label_doctor": {"group": "labels", "label": "Label: doctor name", "default": True, "requires": "medicine_labels"},
    "label_rx_no": {"group": "labels", "label": "Label: Rx / bill number", "default": False, "requires": "medicine_labels"},
    "label_date": {"group": "labels", "label": "Label: date given", "default": True, "requires": "medicine_labels"},
    "label_clinic": {"group": "labels", "label": "Label: clinic / pharmacy name", "default": True,
                     "requires": "medicine_labels"},
    # Billing
    "combined_opd_bill": {"group": "billing", "label": "Medicines on the OPD bill (one combined bill)",
                          "default": False, "requires": "pharmacy_billing"},
}

# Additional settings that are a CHOICE (not on/off). "options" are codes; screen text is in frontend/src/i18n.
ADDITIONAL_CHOICES = {
    "stock_label_format": {"group": "stock_labels", "label": "Stock label size", "options": ["compact", "standard"],
                           "default": "compact", "requires": "pharmacy_stock_labels"},
    "label_format": {"group": "labels", "label": "Default label format", "options": ["compact", "standard", "detailed"],
                     "default": "standard", "requires": "medicine_labels"},
}
