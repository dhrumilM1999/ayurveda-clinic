"""
SAFE TO EDIT: the fixed words printed on prescriptions, certificates, follow-up cards and Prakriti reports,
in English (en), Gujarati (gu) and Hindi (hi). The print-out uses the patient's language.
Change the text on the right; keep the keys on the left. Medicine names and the doctor's own notes are
printed as written.
"""

WORDS = {
    "en": {
        "prescription": "Prescription", "patient": "Patient", "age": "Age", "years": "yrs", "date": "Date",
        "male": "Male", "female": "Female", "other": "Other", "patient_id": "Patient ID", "token": "Token",
        "vitals": "Vitals", "bp": "BP", "pulse": "Pulse", "weight": "Weight", "temperature": "Temp",
        "complaints": "Complaints", "diagnosis": "Diagnosis", "medicine": "Medicine", "dose": "Dose",
        "morning": "Morning", "noon": "Noon", "night": "Night", "when": "When", "with": "With", "with_x": "with {x}",
        "days": "Days", "qty": "Qty", "instructions": "Instructions", "advice": "Diet & lifestyle advice",
        "follow_up": "Next visit", "doctor_sign": "Doctor's signature", "reg_no": "Reg. No.",
        "verify": "Scan to check this document", "duplicate": "DUPLICATE COPY", "rx_no": "Rx No.",
        "follow_up_card": "Follow-up card", "please_come": "Please come for your next check-up on",
        "bring": "Please bring this card and your old prescriptions.", "clinic_phone": "Phone",
        "certificate_no": "Certificate No.", "cancelled": "CANCELLED", "notes": "Notes",
        "medical_title": "Medical Certificate", "fitness_title": "Fitness Certificate", "general_title": "Certificate",
        "certify": "This is to certify that", "was_examined": "was examined by me on",
        "suffering": "and is suffering from", "rest_advised": "Rest is advised from", "to": "to",
        "fit_from": "is now fit to resume normal duties from", "remarks": "Remarks",
        "prakriti_report": "Prakriti (body constitution) report", "prakriti_type": "Prakriti",
        "assessed_on": "Assessed on", "answered": "questions answered", "guidance": "General guidance",
        "vata": "Vata", "pitta": "Pitta", "kapha": "Kapha", "sama": "Sama (balanced)",
        "therapy_plan": "Therapy plan", "plan_name": "Plan", "therapy": "Therapy", "sessions": "Sessions", "time": "Time", "therapist": "Therapist", "room": "Room", "schedule": "Booked sessions", "no_sessions_yet": "Sessions will be booked soon.", "before_after": "Before and after the therapy", "agreed_on": "Patient agreed on", "stage_purva": "Preparation (Purvakarma)", "stage_pradhana": "Main procedure (Pradhanakarma)", "stage_paschat": "After-care (Paschatkarma)", "stage_other": "Other therapy", "plan_note": "Please come on time, wear loose clothes and tell us about any fever, cold or new problem.",
        "investigations": "Tests advised",
        "lab_order": "Lab test order", "lab": "Lab", "urgent": "URGENT", "ordered_tests": "Tests to be done",
        "lab_note": "Please give the report to the patient.",
    },
    "gu": {
        "prescription": "પ્રિસ્ક્રિપ્શન", "patient": "દર્દી", "age": "ઉંમર", "years": "વર્ષ", "date": "તારીખ",
        "male": "પુરુષ", "female": "સ્ત્રી", "other": "અન્ય", "patient_id": "દર્દી ID", "token": "ટોકન",
        "vitals": "વાઇટલ્સ", "bp": "BP", "pulse": "નાડી", "weight": "વજન", "temperature": "તાપમાન",
        "complaints": "તકલીફો", "diagnosis": "નિદાન", "medicine": "દવા", "dose": "માત્રા",
        "morning": "સવાર", "noon": "બપોર", "night": "રાત", "when": "ક્યારે", "with": "સાથે", "with_x": "{x} સાથે",
        "days": "દિવસ", "qty": "જથ્થો", "instructions": "સૂચના", "advice": "આહાર અને જીવનશૈલી સલાહ",
        "follow_up": "આગલી મુલાકાત", "doctor_sign": "ડૉક્ટરની સહી", "reg_no": "રજિ. નં.",
        "verify": "આ દસ્તાવેજ તપાસવા સ્કેન કરો", "duplicate": "ડુપ્લિકેટ નકલ", "rx_no": "Rx નં.",
        "follow_up_card": "ફોલો-અપ કાર્ડ", "please_come": "કૃપા કરી આગલી તપાસ માટે આવો",
        "bring": "આ કાર્ડ અને જૂના પ્રિસ્ક્રિપ્શન સાથે લાવજો.", "clinic_phone": "ફોન",
        "certificate_no": "પ્રમાણપત્ર નં.", "cancelled": "રદ", "notes": "નોંધ",
        "medical_title": "મેડિકલ પ્રમાણપત્ર", "fitness_title": "ફિટનેસ પ્રમાણપત્ર", "general_title": "પ્રમાણપત્ર",
        "certify": "આથી પ્રમાણિત કરવામાં આવે છે કે", "was_examined": "ની મેં તપાસ કરી તારીખ",
        "suffering": "અને તેઓ આ તકલીફથી પીડાય છે:", "rest_advised": "આરામની સલાહ તારીખ", "to": "થી",
        "fit_from": "હવે સામાન્ય કામ ફરી શરૂ કરવા યોગ્ય છે, તારીખ", "remarks": "નોંધ",
        "prakriti_report": "પ્રકૃતિ (શરીર પ્રકૃતિ) રિપોર્ટ", "prakriti_type": "પ્રકૃતિ",
        "assessed_on": "તપાસ તારીખ", "answered": "પ્રશ્નોના જવાબ", "guidance": "સામાન્ય માર્ગદર્શન",
        "vata": "વાત", "pitta": "પિત્ત", "kapha": "કફ", "sama": "સમ (સંતુલિત)",
        "therapy_plan": "થેરાપી પ્લાન", "plan_name": "પ્લાન", "therapy": "થેરાપી", "sessions": "સેશન", "time": "સમય", "therapist": "થેરાપિસ્ટ", "room": "રૂમ", "schedule": "બુક થયેલા સેશન", "no_sessions_yet": "સેશન જલ્દી બુક થશે.", "before_after": "થેરાપી પહેલાં અને પછી", "agreed_on": "દર્દીની સંમતિ તારીખ", "stage_purva": "તૈયારી (પૂર્વકર્મ)", "stage_pradhana": "મુખ્ય પ્રક્રિયા (પ્રધાનકર્મ)", "stage_paschat": "પછીની કાળજી (પશ્ચાત્કર્મ)", "stage_other": "અન્ય થેરાપી", "plan_note": "કૃપા કરી સમયસર આવો, ઢીલાં કપડાં પહેરો અને તાવ, શરદી કે નવી તકલીફ હોય તો જણાવો.",
        "investigations": "કરાવવાના ટેસ્ટ",
        "lab_order": "લેબ ટેસ્ટ ઓર્ડર", "lab": "લેબ", "urgent": "તાત્કાલિક", "ordered_tests": "કરવાના ટેસ્ટ",
        "lab_note": "કૃપા કરી રિપોર્ટ દર્દીને આપો.",
    },
    "hi": {
        "prescription": "प्रिस्क्रिप्शन", "patient": "मरीज़", "age": "उम्र", "years": "वर्ष", "date": "तारीख़",
        "male": "पुरुष", "female": "स्त्री", "other": "अन्य", "patient_id": "मरीज़ ID", "token": "टोकन",
        "vitals": "वाइटल्स", "bp": "BP", "pulse": "नाड़ी", "weight": "वज़न", "temperature": "तापमान",
        "complaints": "तकलीफ़ें", "diagnosis": "निदान", "medicine": "दवा", "dose": "खुराक",
        "morning": "सुबह", "noon": "दोपहर", "night": "रात", "when": "कब", "with": "साथ", "with_x": "{x} के साथ",
        "days": "दिन", "qty": "मात्रा", "instructions": "निर्देश", "advice": "आहार और जीवनशैली सलाह",
        "follow_up": "अगली विज़िट", "doctor_sign": "डॉक्टर के हस्ताक्षर", "reg_no": "रजि. नं.",
        "verify": "यह दस्तावेज़ जाँचने के लिए स्कैन करें", "duplicate": "डुप्लिकेट कॉपी", "rx_no": "Rx नं.",
        "follow_up_card": "फ़ॉलो-अप कार्ड", "please_come": "कृपया अगली जाँच के लिए आएँ",
        "bring": "यह कार्ड और पुराने प्रिस्क्रिप्शन साथ लाएँ।", "clinic_phone": "फ़ोन",
        "certificate_no": "प्रमाणपत्र नं.", "cancelled": "रद्द", "notes": "नोट",
        "medical_title": "मेडिकल प्रमाणपत्र", "fitness_title": "फ़िटनेस प्रमाणपत्र", "general_title": "प्रमाणपत्र",
        "certify": "प्रमाणित किया जाता है कि", "was_examined": "की मैंने जाँच की तारीख़",
        "suffering": "और वे इस तकलीफ़ से पीड़ित हैं:", "rest_advised": "आराम की सलाह तारीख़", "to": "से",
        "fit_from": "अब सामान्य काम फिर से शुरू करने योग्य हैं, तारीख़", "remarks": "टिप्पणी",
        "prakriti_report": "प्रकृति (शरीर प्रकृति) रिपोर्ट", "prakriti_type": "प्रकृति",
        "assessed_on": "जाँच तारीख़", "answered": "प्रश्नों के उत्तर", "guidance": "सामान्य मार्गदर्शन",
        "vata": "वात", "pitta": "पित्त", "kapha": "कफ", "sama": "सम (संतुलित)",
        "therapy_plan": "थेरेपी प्लान", "plan_name": "प्लान", "therapy": "थेरेपी", "sessions": "सेशन", "time": "समय", "therapist": "थेरेपिस्ट", "room": "कमरा", "schedule": "बुक किए गए सेशन", "no_sessions_yet": "सेशन जल्दी बुक होंगे।", "before_after": "थेरेपी से पहले और बाद में", "agreed_on": "मरीज़ की सहमति की तारीख़", "stage_purva": "तैयारी (पूर्वकर्म)", "stage_pradhana": "मुख्य प्रक्रिया (प्रधानकर्म)", "stage_paschat": "बाद की देखभाल (पश्चातकर्म)", "stage_other": "अन्य थेरेपी", "plan_note": "कृपया समय पर आएँ, ढीले कपड़े पहनें और बुखार, सर्दी या कोई नई तकलीफ़ हो तो बताएँ।",
        "investigations": "करवाने के टेस्ट",
        "lab_order": "लैब टेस्ट ऑर्डर", "lab": "लैब", "urgent": "तत्काल", "ordered_tests": "किए जाने वाले टेस्ट",
        "lab_note": "कृपया रिपोर्ट मरीज़ को दें.",
    },
}

# General, well-known guidance printed on the Prakriti report for the main dosha. The doctor's own advice
# on the prescription always comes first. SAFE TO EDIT (keep it short).
PRAKRITI_GUIDANCE = {
    "en": {
        "vata": "Keep a regular daily routine and sleep time. Prefer warm, freshly cooked, slightly oily food. Avoid cold, dry and stale food, fasting and late nights. Daily oil massage (abhyanga) helps.",
        "pitta": "Prefer cool, fresh, less spicy food and enough water. Avoid too much sour, salty, fried and spicy food, anger and long sun exposure. Keep meal times regular.",
        "kapha": "Stay active with daily exercise. Prefer light, warm, less oily food with spices like ginger. Avoid heavy, sweet, cold food, day sleep and overeating.",
        "sama": "Your doshas are balanced. Keep a regular routine, seasonal diet (ritucharya) and daily exercise to stay in balance.",
    },
    "gu": {
        "vata": "રોજનો નિયમિત દિનક્રમ અને ઊંઘનો સમય રાખો. ગરમ, તાજો રાંધેલો, થોડો સ્નિગ્ધ ખોરાક લો. ઠંડો, સૂકો, વાસી ખોરાક, ઉપવાસ અને ઉજાગરા ટાળો. રોજ તેલ માલિશ (અભ્યંગ) લાભદાયી છે.",
        "pitta": "ઠંડો, તાજો, ઓછો તીખો ખોરાક અને પૂરતું પાણી લો. વધુ ખાટું, ખારું, તળેલું, તીખું, ગુસ્સો અને લાંબો તડકો ટાળો. જમવાનો સમય નિયમિત રાખો.",
        "kapha": "રોજ કસરત કરી સક્રિય રહો. હળવો, ગરમ, ઓછો તેલવાળો, આદુ જેવા મસાલાવાળો ખોરાક લો. ભારે, મીઠો, ઠંડો ખોરાક, દિવસે ઊંઘ અને વધુ જમવાનું ટાળો.",
        "sama": "તમારા દોષ સંતુલિત છે. સંતુલન જાળવવા નિયમિત દિનક્રમ, ઋતુ પ્રમાણે આહાર (ઋતુચર્યા) અને રોજ કસરત રાખો.",
    },
    "hi": {
        "vata": "रोज़ नियमित दिनचर्या और सोने का समय रखें। गरम, ताज़ा पका, थोड़ा स्निग्ध भोजन लें। ठंडा, सूखा, बासी भोजन, उपवास और देर रात जागना टालें। रोज़ तेल मालिश (अभ्यंग) लाभकारी है।",
        "pitta": "ठंडा, ताज़ा, कम तीखा भोजन और पर्याप्त पानी लें। ज़्यादा खट्टा, नमकीन, तला, तीखा, ग़ुस्सा और लंबी धूप टालें। भोजन का समय नियमित रखें।",
        "kapha": "रोज़ व्यायाम करके सक्रिय रहें। हल्का, गरम, कम तेल वाला, अदरक जैसे मसालों वाला भोजन लें। भारी, मीठा, ठंडा भोजन, दिन में सोना और ज़्यादा खाना टालें।",
        "sama": "आपके दोष संतुलित हैं। संतुलन बनाए रखने के लिए नियमित दिनचर्या, ऋतु अनुसार आहार (ऋतुचर्या) और रोज़ व्यायाम रखें।",
    },
}


# Words for the DETAILED prescription (full check-up summary). SAFE TO EDIT, like the words above.
DETAILED_WORDS = {
    "en": {
        "detailed_title": "Check-up summary and prescription", "history": "History / clinical notes",
        "examination": "Examination", "medical_history": "Known conditions", "allergies": "Allergies",
        "current_medicines": "Other medicines being taken", "height": "Height", "bmi": "BMI", "spo2": "SpO2",
        "resp_rate": "Resp. rate", "since_x": "since {x}", "severity": "severity", "provisional": "provisional",
        "final": "final", "prakriti_result": "Prakriti result", "duration": "for",
    },
    "gu": {
        "detailed_title": "તપાસનો સારાંશ અને પ્રિસ્ક્રિપ્શન", "history": "ઇતિહાસ / તપાસ નોંધ",
        "examination": "તપાસ", "medical_history": "જાણીતી બીમારીઓ", "allergies": "એલર્જી",
        "current_medicines": "ચાલુ અન્ય દવાઓ", "height": "ઊંચાઈ", "bmi": "BMI", "spo2": "SpO2",
        "resp_rate": "શ્વાસ દર", "since_x": "{x} થી", "severity": "તીવ્રતા", "provisional": "પ્રાથમિક",
        "final": "અંતિમ", "prakriti_result": "પ્રકૃતિ પરિણામ", "duration": "સમય",
    },
    "hi": {
        "detailed_title": "जाँच का सारांश और प्रिस्क्रिप्शन", "history": "इतिहास / जाँच नोट",
        "examination": "जाँच", "medical_history": "ज्ञात बीमारियाँ", "allergies": "एलर्जी",
        "current_medicines": "चल रही अन्य दवाइयाँ", "height": "लंबाई", "bmi": "BMI", "spo2": "SpO2",
        "resp_rate": "साँस दर", "since_x": "{x} से", "severity": "गंभीरता", "provisional": "प्रारंभिक",
        "final": "अंतिम", "prakriti_result": "प्रकृति परिणाम", "duration": "अवधि",
    },
}


def words_for(lang: str) -> dict:
    base = WORDS.get(lang) or WORDS["en"]
    return {**base, **(DETAILED_WORDS.get(lang) or DETAILED_WORDS["en"])}


# SAFE TO EDIT: the lines on the left of the "Ayurveda case sheet" prescription design (Settings -> Branch details ->
# Prescription design), printed exactly as written, in this order. On the right: the check-up answers that fill the
# line (the first one filled in is used; "occupation" = the patient's occupation). A line with nothing filled in is
# printed empty, for the doctor to write by hand. Add a line: ("Label", ["answer_key"]).
CASE_SHEET_LINES = [
    ("Agni", ["agni"]),
    ("Koshta", ["koshta"]),
    ("Sama / Nirama", ["sama_nirama", "ama"]),
    ("Mutra", ["mutra", "urine_day"]),
    ("Purisha", ["mala", "bowel_per_day"]),
    ("Artava", ["artava"]),
    ("Sweda", ["sweda"]),
    ("Udgara", ["udgar"]),
    ("Nidra", ["sleep"]),
    ("Svapna", ["svapna"]),
    ("Occupation", ["occupation"]),
    ("Dosha", ["vikriti"]),
    ("Dushya", ["dushya"]),
    ("Srotas", ["srotas"]),
]
# A short line is drawn above this line (it must match a label above exactly)
CASE_SHEET_SPLIT_BEFORE = "Dosha"
# Headings of the case sheet (printed as written)
CASE_SHEET_WORDS_BY_LANGUAGE = {
    "en": {"symptoms": "Symptoms", "diagnosis": "Diagnosis", "advice": "Advice / Pathya", "next_visit": "Next visit",
           "name": "Name.", "age_sex": "Age/Sex.", "date": "Date.", "weight": "Wt."},
    "gu": {"symptoms": "તકલીફો", "diagnosis": "નિદાન", "advice": "સલાહ / પથ્ય", "next_visit": "આગલી મુલાકાત",
           "name": "નામ.", "age_sex": "ઉંમર/જાતિ.", "date": "તારીખ.", "weight": "વજન."},
    "hi": {"symptoms": "तकलीफ़ें", "diagnosis": "निदान", "advice": "सलाह / पथ्य", "next_visit": "अगली मुलाक़ात",
           "name": "नाम.", "age_sex": "आयु/लिंग.", "date": "दिनांक.", "weight": "वज़न."},
}
CASE_SHEET_WORDS = CASE_SHEET_WORDS_BY_LANGUAGE["en"]

# The Ayurveda case-sheet line labels (CASE_SHEET_LINES above) in Gujarati and Hindi. A label that is not here is
# printed as written, so a line you add yourself still works.
CASE_SHEET_LABELS = {
    "gu": {"Agni": "અગ્નિ", "Koshta": "કોષ્ઠ", "Sama / Nirama": "સામ / નિરામ", "Mutra": "મૂત્ર", "Purisha": "પુરીષ",
           "Artava": "આર્તવ", "Sweda": "સ્વેદ", "Udgara": "ઉદ્ગાર", "Nidra": "નિદ્રા", "Svapna": "સ્વપ્ન",
           "Occupation": "વ્યવસાય", "Dosha": "દોષ", "Dushya": "દૂષ્ય", "Srotas": "સ્રોતસ"},
    "hi": {"Agni": "अग्नि", "Koshta": "कोष्ठ", "Sama / Nirama": "सम / निराम", "Mutra": "मूत्र", "Purisha": "पुरीष",
           "Artava": "आर्तव", "Sweda": "स्वेद", "Udgara": "उद्गार", "Nidra": "निद्रा", "Svapna": "स्वप्न",
           "Occupation": "व्यवसाय", "Dosha": "दोष", "Dushya": "दूष्य", "Srotas": "स्रोतस"},
}
