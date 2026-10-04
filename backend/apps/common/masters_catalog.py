"""
SAFE TO EDIT: the starting values of every dropdown list (master data).

These values are copied into the database for each organization (on start, only the
ones that are missing). After that, staff can edit them in the app, so changing this
file does NOT change values that already exist in the database.

Each value: (code, English, Gujarati, Hindi). The code is an internal short name; never change
it after the value is in use.
"""

CATEGORIES = {
    "title": "Title (Mr / Mrs ...)",
    "blood_group": "Blood group",
    "marital_status": "Marital status",
    "relation": "Relation",
    "referral_source": "How the patient heard of us",
    "medical_condition": "Medical history (conditions)",
    "allergy_type": "Allergy type",
    "document_type": "Document type",
}

DEFAULT_VALUES = {
    "title": [
        ("mr", "Mr", "શ્રી", "श्री"),
        ("mrs", "Mrs", "શ્રીમતી", "श्रीमती"),
        ("ms", "Ms", "સુશ્રી", "सुश्री"),
        ("miss", "Miss", "કુમારી", "कुमारी"),
        ("dr", "Dr", "ડૉ.", "डॉ."),
        ("master", "Master", "માસ્ટર", "मास्टर"),
        ("baby", "Baby", "બેબી", "बेबी"),
    ],
    "blood_group": [
        ("a_pos", "A+", "A+", "A+"), ("a_neg", "A−", "A−", "A−"),
        ("b_pos", "B+", "B+", "B+"), ("b_neg", "B−", "B−", "B−"),
        ("ab_pos", "AB+", "AB+", "AB+"), ("ab_neg", "AB−", "AB−", "AB−"),
        ("o_pos", "O+", "O+", "O+"), ("o_neg", "O−", "O−", "O−"),
    ],
    "marital_status": [
        ("single", "Single", "અપરિણીત", "अविवाहित"),
        ("married", "Married", "પરિણીત", "विवाहित"),
        ("widowed", "Widowed", "વિધવા / વિધુર", "विधवा / विधुर"),
        ("divorced", "Divorced", "છૂટાછેડા", "तलाकशुदा"),
    ],
    "relation": [
        ("father", "Father", "પિતા", "पिता"),
        ("mother", "Mother", "માતા", "माता"),
        ("spouse", "Spouse", "પતિ / પત્ની", "पति / पत्नी"),
        ("son", "Son", "પુત્ર", "पुत्र"),
        ("daughter", "Daughter", "પુત્રી", "पुत्री"),
        ("brother", "Brother", "ભાઈ", "भाई"),
        ("sister", "Sister", "બહેન", "बहन"),
        ("guardian", "Guardian", "વાલી", "अभिभावक"),
        ("friend", "Friend", "મિત્ર", "मित्र"),
        ("other", "Other", "અન્ય", "अन्य"),
    ],
    "referral_source": [
        ("walk_in", "Walk-in / Self", "જાતે આવ્યા", "स्वयं आए"),
        ("doctor", "Doctor", "ડૉક્ટર", "डॉक्टर"),
        ("family_friend", "Family / Friend", "કુટુંબ / મિત્ર", "परिवार / मित्र"),
        ("existing_patient", "Existing patient", "હાલના દર્દી", "मौजूदा मरीज़"),
        ("google", "Google / Website", "Google / વેબસાઇટ", "Google / वेबसाइट"),
        ("social_media", "Social media", "સોશિયલ મીડિયા", "सोशल मीडिया"),
        ("newspaper", "Newspaper / Hoarding", "છાપું / હોર્ડિંગ", "अख़बार / होर्डिंग"),
        ("camp", "Health camp", "આરોગ્ય કેમ્પ", "स्वास्थ्य शिविर"),
    ],
    "medical_condition": [
        ("diabetes", "Diabetes", "ડાયાબિટીસ", "मधुमेह"),
        ("hypertension", "High BP (Hypertension)", "હાઈ બીપી", "उच्च रक्तचाप"),
        ("thyroid", "Thyroid", "થાઇરોઇડ", "थायरॉइड"),
        ("asthma", "Asthma", "દમ / અસ્થમા", "दमा / अस्थमा"),
        ("heart", "Heart disease", "હૃદય રોગ", "हृदय रोग"),
        ("kidney", "Kidney disease", "કિડનીની બીમારી", "गुर्दे की बीमारी"),
        ("liver", "Liver disease", "લીવરની બીમારી", "यकृत की बीमारी"),
        ("arthritis", "Arthritis / Joint pain", "સંધિવા / સાંધાનો દુખાવો", "गठिया / जोड़ों का दर्द"),
        ("acidity", "Acidity / GERD", "એસિડિટી", "एसिडिटी"),
        ("cholesterol", "High cholesterol", "કોલેસ્ટ્રોલ", "कोलेस्ट्रॉल"),
        ("obesity", "Obesity", "મેદસ્વિતા", "मोटापा"),
        ("pcod", "PCOD / PCOS", "PCOD / PCOS", "PCOD / PCOS"),
        ("migraine", "Migraine", "માઇગ્રેન", "माइग्रेन"),
        ("skin", "Skin disease", "ચામડીનો રોગ", "त्वचा रोग"),
        ("cancer", "Cancer (past or present)", "કેન્સર (હાલ કે પહેલાં)", "कैंसर (पहले या अभी)"),
        ("pregnant", "Pregnant", "ગર્ભવતી", "गर्भवती"),
        ("breastfeeding", "Breastfeeding", "સ્તનપાન", "स्तनपान"),
    ],
    "allergy_type": [
        ("drug", "Medicine", "દવા", "दवा"),
        ("food", "Food", "ખોરાક", "भोजन"),
        ("environment", "Dust / Pollen / Other environment", "ધૂળ / પરાગ / વાતાવરણ", "धूल / पराग / वातावरण"),
        ("other", "Other", "અન્ય", "अन्य"),
    ],
    "document_type": [
        ("lab_report", "Lab report", "લેબ રિપોર્ટ", "लैब रिपोर्ट"),
        ("old_prescription", "Old prescription", "જૂનું પ્રિસ્ક્રિપ્શન", "पुराना प्रिस्क्रिप्शन"),
        ("scan", "X-ray / Scan", "એક્સ-રે / સ્કેન", "एक्स-रे / स्कैन"),
        ("discharge", "Discharge summary", "ડિસ્ચાર્જ સારાંશ", "डिस्चार्ज सारांश"),
        ("consent_form", "Signed consent form", "સહી કરેલું સંમતિ પત્રક", "हस्ताक्षरित सहमति पत्र"),
        ("other", "Other", "અન્ય", "अन्य"),
    ],
}
