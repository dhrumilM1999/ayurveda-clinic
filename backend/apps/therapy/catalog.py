"""
SAFE TO EDIT: the starting list of therapies a new clinic gets. Each line:
(name, Gujarati, Hindi, stage, minutes, usual material)
stage: purva = preparation, pradhana = main procedure, paschat = after-care, other.
Clinics can change, add or hide therapies on the Therapies screen; this list is only the starting point.
"""
THERAPIES = [
    # Purvakarma (preparation)
    ("Snehapana (internal oiling)", "સ્નેહપાન", "स्नेहपान", "purva", 15, "Medicated ghee"),
    ("Abhyanga (oil massage)", "અભ્યંગ", "अभ्यंग", "purva", 45, "Sesame oil"),
    ("Swedana (herbal steam)", "સ્વેદન", "स्वेदन", "purva", 20, "Herbal steam"),
    ("Pinda Sweda (bolus massage)", "પિંડ સ્વેદ", "पिंड स्वेद", "purva", 60, "Shashtika rice / herbal bolus"),
    ("Patra Pinda Sweda (leaf bolus)", "પત્ર પિંડ સ્વેદ", "पत्र पिंड स्वेद", "purva", 60, "Medicated leaves"),
    ("Udvartana (dry powder massage)", "ઉદ્વર્તન", "उद्वर्तन", "purva", 40, "Herbal powder"),
    # Pradhanakarma (the five main cleansing procedures)
    ("Vamana (therapeutic emesis)", "વમન", "वमन", "pradhana", 120, "Madanaphala decoction"),
    ("Virechana (purgation)", "વિરેચન", "विरेचन", "pradhana", 60, "Trivrit / Avipattikar"),
    ("Basti - Anuvasana (oil enema)", "અનુવાસન બસ્તિ", "अनुवासन बस्ति", "pradhana", 45, "Medicated oil"),
    ("Basti - Niruha (decoction enema)", "નિરૂહ બસ્તિ", "निरूह बस्ति", "pradhana", 45, "Kashaya with honey and salt"),
    ("Nasya (nasal medication)", "નસ્ય", "नस्य", "pradhana", 30, "Anu taila"),
    ("Raktamokshana (bloodletting)", "રક્તમોક્ષણ", "रक्तमोक्षण", "pradhana", 45, "Jalauka / sterile set"),
    # Other common therapies
    ("Shirodhara", "શિરોધારા", "शिरोधारा", "other", 45, "Medicated oil / buttermilk"),
    ("Shiro Abhyanga (head massage)", "શિરો અભ્યંગ", "शिरो अभ्यंग", "other", 25, "Medicated oil"),
    ("Shirobasti", "શિરોબસ્તિ", "शिरोबस्ति", "other", 45, "Medicated oil"),
    ("Kati Basti (lower back)", "કટિ બસ્તિ", "कटि बस्ति", "other", 40, "Warm medicated oil"),
    ("Janu Basti (knee)", "જાનુ બસ્તિ", "जानु बस्ति", "other", 40, "Warm medicated oil"),
    ("Greeva Basti (neck)", "ગ્રીવા બસ્તિ", "ग्रीवा बस्ति", "other", 40, "Warm medicated oil"),
    ("Netra Tarpana (eye)", "નેત્ર તર્પણ", "नेत्र तर्पण", "other", 30, "Medicated ghee"),
    ("Karna Purana (ear)", "કર્ણ પૂરણ", "कर्ण पूरण", "other", 15, "Medicated oil"),
    ("Takradhara (buttermilk pour)", "તક્રધારા", "तक्रधारा", "other", 45, "Medicated buttermilk"),
    ("Upanaha (herbal poultice)", "ઉપનાહ", "उपनाह", "other", 30, "Herbal paste"),
    ("Agnikarma (thermal cautery)", "અગ્નિકર્મ", "अग्निकर्म", "other", 20, ""),
    ("Lepa (herbal paste)", "લેપ", "लेप", "other", 25, "Herbal paste"),
    # Paschatkarma (after-care)
    ("Samsarjana krama (diet after cleansing)", "સંસર્જન ક્રમ", "संसर्जन क्रम", "paschat", 10, "Graded diet"),
    ("Dhumapana (medicated smoke)", "ધૂમપાન", "धूमपान", "paschat", 10, "Herbal smoke"),
    ("Gandusha / Kavala (oil pulling)", "ગંડૂષ", "गंडूष", "paschat", 10, "Medicated oil"),
]
