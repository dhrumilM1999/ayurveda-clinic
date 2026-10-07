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
    ("अग्नि", ["agni"]),
    ("कोष्ठ", ["koshta"]),
    ("साम / नीराम", ["sama_nirama", "ama"]),
    ("मूत्र प्रवृत्ति", ["mutra", "urine_day"]),
    ("पुरीष प्रवृत्ति", ["mala", "bowel_per_day"]),
    ("आर्तव प्रवृत्ति", ["artava"]),
    ("स्वेद प्रवृत्ति", ["sweda"]),
    ("उद्गार", ["udgar"]),
    ("निद्रा", ["sleep"]),
    ("स्वप्न", ["svapna"]),
    ("कार्यक्षेत्र", ["occupation"]),
    ("दोष", ["vikriti"]),
    ("दूष्य", ["dushya"]),
    ("स्रोतस", ["srotas"]),
]
# Headings of the case sheet (printed as written)
CASE_SHEET_WORDS = {"symptoms": "लक्षण", "diagnosis": "निदान", "advice": "पथ्य / सलाह", "next_visit": "पुनः दर्शन"}
