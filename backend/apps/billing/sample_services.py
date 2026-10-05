"""
SAFE TO EDIT: SAMPLE services & charges for a new clinic's OPD bill (made-up prices - change them in the app
under "Fees & services"). Each: (name, Gujarati, Hindi, category code, price in rupees).
GST is 0 (health care services are usually exempt) - confirm with your CA.
"""
from decimal import Decimal

SERVICES = [
    ("Nadi Pariksha (pulse examination)", "નાડી પરીક્ષા", "नाड़ी परीक्षा", "examination", 100),
    ("Agnikarma", "અગ્નિકર્મ", "अग्निकर्म", "procedure", 500),
    ("Viddhakarma", "વિદ્ધકર્મ", "विद्धकर्म", "procedure", 400),
    ("Jalaukavacharana (leech therapy)", "જલૌકાવચરણ", "जलौकावचरण", "procedure", 600),
    ("Abhyanga (oil massage)", "અભ્યંગ", "अभ्यंग", "panchakarma", 800),
    ("Shirodhara", "શિરોધારા", "शिरोधारा", "panchakarma", 1200),
    ("Dressing", "ડ્રેસિંગ", "ड्रेसिंग", "dressing", 150),
    ("Medical certificate", "મેડિકલ પ્રમાણપત્ર", "मेडिकल प्रमाणपत्र", "certificate", 200),
]


def add_sample_services(organization) -> int:
    from apps.common.models import MasterValue

    from .models import ServiceCharge

    categories = {m.code: m for m in MasterValue.objects.filter(organization=organization, category="service_category")}
    added = 0
    for order, (name, gu, hi, category, price) in enumerate(SERVICES):
        _, created = ServiceCharge.objects.get_or_create(
            organization=organization, name=name,
            defaults={"name_gu": gu, "name_hi": hi, "category": categories.get(category), "price": Decimal(price),
                      "gst_rate": 0, "sort_order": order, "is_sample": True},
        )
        added += created
    return added
