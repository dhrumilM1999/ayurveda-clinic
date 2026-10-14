"""
SAFE TO EDIT: the starting list of therapies a new clinic gets. Each line:
(name, Gujarati, Hindi, stage, minutes, usual material)
INSTRUCTIONS (below) = the general before / after advice printed on the patient's therapy plan. These are only a
starting point: the DOCTOR must read and change them for the clinic.
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

# Therapy name -> advice printed on the patient's plan (English). Keep it short. SAFE TO EDIT.
INSTRUCTIONS = {
    "Abhyanga (oil massage)": "Come with an empty or light stomach (2 hours after a meal). Bathe with warm water after 30-45 minutes. Avoid cold wind, cold drinks and day sleep for the day.",
    "Swedana (herbal steam)": "Do not come on a very full or a completely empty stomach. Drink warm water after the steam and rest. Avoid cold water bath for one hour.",
    "Shirodhara": "Wash your hair only after one day, with warm water. Avoid head bath with cold water, loud noise, screens and late nights on the day.",
    "Basti - Anuvasana (oil enema)": "Take a light meal (not heavy or oily) before. Pass urine and stool before the treatment. Eat light, warm food afterwards; avoid cold, dry and stale food.",
    "Basti - Niruha (decoction enema)": "Come on an empty stomach as advised by the doctor. Pass urine and stool before. After the treatment eat only light, warm food (as advised) and rest.",
    "Vamana (therapeutic emesis)": "Follow the preparation (oil intake, steam) exactly as the doctor told. Come on the fixed day on an empty stomach. After the treatment take only the graded light diet given by the doctor and rest for the day.",
    "Virechana (purgation)": "Follow the preparation (oil intake, steam) as the doctor told. Eat only light, easily digestible food the day before. After the treatment follow the graded diet; avoid spicy, oily and cold food.",
    "Nasya (nasal medication)": "Come on an empty stomach. Avoid cold wind, dust and head bath for one hour afterwards. Do not talk loudly or sleep right after the treatment.",
    "Kati Basti (lower back)": "Avoid bending, lifting weights and cold exposure of the back on that day. Keep the back warm.",
    "Janu Basti (knee)": "Avoid climbing stairs and long walking on that day. Keep the knee warm and covered.",
    "Raktamokshana (bloodletting)": "Tell the doctor about any blood thinner or bleeding problem. Keep the area clean and dry; follow the dressing advice given.",
    "Samsarjana krama (diet after cleansing)": "Follow the diet steps given by the doctor day by day (thin rice gruel, then soft rice and dal, then normal food). Do not skip a step.",
}
