"""
SAFE TO EDIT: the starting Ayurveda check-up templates (Ashtavidha, Dashavidha, Prakriti, Agni & habits).

How it works
- Each template is copied into the database for each clinic (only if it is missing).
  After that the copy in the database is used, so editing this file does not change
  templates that already exist. (A screen to edit templates comes later.)
- A template has fields. Field types:
    "choice"  one answer (buttons)          "multi"  several answers (tick buttons)
    "number"  a number with a unit          "text"   free notes
- "questionnaire" templates (Prakriti) give each answer to a dosha (vata / pitta / kapha)
  and the software counts the score.
- Every label has English (en), Gujarati (gu) and Hindi (hi).
- Never change a field "key" or an option "value" after the template is in use (old visits use them).
  To change the meaning, raise "version".

The Prakriti questions are a SAMPLE — the doctor should review and replace them.
"""


def L(en, gu, hi):
    return {"en": en, "gu": gu, "hi": hi}


def opts(*rows):
    """rows of (value, en, gu, hi) -> option list"""
    return [{"value": v, "label": L(en, gu, hi)} for v, en, gu, hi in rows]


DOSHA_TYPES = opts(
    ("vata", "Vata", "વાત", "वात"),
    ("pitta", "Pitta", "પિત્ત", "पित्त"),
    ("kapha", "Kapha", "કફ", "कफ"),
    ("vata_pitta", "Vata-Pitta", "વાત-પિત્ત", "वात-पित्त"),
    ("vata_kapha", "Vata-Kapha", "વાત-કફ", "वात-कफ"),
    ("pitta_kapha", "Pitta-Kapha", "પિત્ત-કફ", "पित्त-कफ"),
    ("sama", "Sama (balanced)", "સમ (સંતુલિત)", "सम (संतुलित)"),
)

GRADES = opts(
    ("pravara", "Good (Pravara)", "ઉત્તમ (પ્રવર)", "उत्तम (प्रवर)"),
    ("madhyama", "Medium (Madhyama)", "મધ્યમ", "मध्यम"),
    ("avara", "Low (Avara)", "ઓછું (અવર)", "कम (अवर)"),
)

NOTES = {"key": "notes", "type": "text", "label": L("Notes", "નોંધ", "नोट")}


TEMPLATES = [
    # ---------------------------------------------------------------------------------
    {
        "code": "ashtavidha",
        "version": 1,
        "kind": "form",
        "name": L("Ashtavidha Pariksha", "અષ્ટવિધ પરીક્ષા", "अष्टविध परीक्षा"),
        "description": L("Eight-fold examination", "આઠ પ્રકારની પરીક્ષા", "आठ प्रकार की परीक्षा"),
        "fields": [
            {"key": "nadi", "type": "choice", "label": L("Nadi (pulse)", "નાડી", "नाड़ी"), "options": opts(
                ("vata", "Vata - snake-like (Sarpa)", "વાત - સર્પ ગતિ", "वात - सर्प गति"),
                ("pitta", "Pitta - frog-like (Manduka)", "પિત્ત - મંડૂક ગતિ", "पित्त - मंडूक गति"),
                ("kapha", "Kapha - swan-like (Hamsa)", "કફ - હંસ ગતિ", "कफ - हंस गति"),
                ("vata_pitta", "Vata-Pitta", "વાત-પિત્ત", "वात-पित्त"),
                ("vata_kapha", "Vata-Kapha", "વાત-કફ", "वात-कफ"),
                ("pitta_kapha", "Pitta-Kapha", "પિત્ત-કફ", "पित्त-कफ"),
                ("sama", "Sama (balanced)", "સમ", "सम"),
            )},
            {"key": "nadi_rate", "type": "number", "unit": "/min", "min": 30, "max": 200,
             "label": L("Nadi rate", "નાડી ગતિ", "नाड़ी दर")},
            {"key": "mutra", "type": "choice", "label": L("Mutra (urine)", "મૂત્ર", "मूत्र"), "options": opts(
                ("normal", "Normal", "સામાન્ય", "सामान्य"),
                ("pale", "Pale / clear", "ફિક્કું / સાફ", "हल्का / साफ़"),
                ("yellow", "Yellow", "પીળું", "पीला"),
                ("dark", "Dark yellow / reddish", "ઘાટું પીળું / લાલાશ", "गहरा पीला / लालिमा"),
                ("turbid", "Turbid / cloudy", "ડહોળું", "गंदला"),
                ("burning", "With burning", "બળતરા સાથે", "जलन के साथ"),
            )},
            {"key": "mala", "type": "choice", "label": L("Mala (stool)", "મળ", "मल"), "options": opts(
                ("normal", "Normal, well formed", "સામાન્ય", "सामान्य"),
                ("hard", "Hard / constipated", "કઠણ / કબજિયાત", "सख़्त / कब्ज़"),
                ("loose", "Loose", "પાતળો", "पतला"),
                ("sticky", "Sticky, with mucus (Sama)", "ચીકણો, આમ સાથે", "चिपचिपा, आम युक्त"),
                ("irregular", "Irregular", "અનિયમિત", "अनियमित"),
            )},
            {"key": "jihva", "type": "choice", "label": L("Jihva (tongue)", "જિહ્વા (જીભ)", "जिह्वा (जीभ)"), "options": opts(
                ("clean", "Clean (Nirama)", "સાફ (નિરામ)", "साफ़ (निराम)"),
                ("coated", "Coated (Sama)", "છારીવાળી (સામ)", "परत वाली (साम)"),
                ("dry", "Dry / cracked", "સૂકી / ચીરાવાળી", "सूखी / दरार वाली"),
                ("red", "Red / burning", "લાલ / બળતરા", "लाल / जलन"),
                ("pale", "Pale", "ફિક્કી", "पीली/फीकी"),
            )},
            {"key": "shabda", "type": "choice", "label": L("Shabda (voice)", "શબ્દ (અવાજ)", "शब्द (आवाज़)"), "options": opts(
                ("normal", "Normal, clear", "સામાન્ય, સ્પષ્ટ", "सामान्य, स्पष्ट"),
                ("weak", "Weak / low", "નબળો / ધીમો", "कमज़ोर / धीमी"),
                ("hoarse", "Hoarse / dry", "ઘોઘરો / સૂકો", "भारी / सूखी"),
                ("heavy", "Heavy / deep", "ભારે / ઊંડો", "भारी / गहरी"),
            )},
            {"key": "sparsha", "type": "choice", "label": L("Sparsha (touch / skin)", "સ્પર્શ (ત્વચા)", "स्पर्श (त्वचा)"), "options": opts(
                ("normal", "Normal", "સામાન્ય", "सामान्य"),
                ("cold_dry", "Cold, dry, rough (Vata)", "ઠંડી, સૂકી, ખરબચડી (વાત)", "ठंडी, सूखी, खुरदरी (वात)"),
                ("warm", "Warm (Pitta)", "ગરમ (પિત્ત)", "गर्म (पित्त)"),
                ("cool_moist", "Cool, moist, smooth (Kapha)", "ઠંડી, ભીની, લીસી (કફ)", "ठंडी, नम, चिकनी (कफ)"),
            )},
            {"key": "drik", "type": "choice", "label": L("Drik (eyes)", "દૃક (આંખો)", "दृक (आँखें)"), "options": opts(
                ("normal", "Normal", "સામાન્ય", "सामान्य"),
                ("dry", "Dry, dull (Vata)", "સૂકી, નિસ્તેજ (વાત)", "सूखी, फीकी (वात)"),
                ("red_yellow", "Reddish / yellowish (Pitta)", "લાલાશ / પીળાશ (પિત્ત)", "लालिमा / पीलापन (पित्त)"),
                ("white_watery", "White, watery (Kapha)", "સફેદ, પાણીવાળી (કફ)", "सफ़ेद, पानी वाली (कफ)"),
            )},
            {"key": "akriti", "type": "choice", "label": L("Akriti (build)", "આકૃતિ (બાંધો)", "आकृति (बनावट)"), "options": opts(
                ("krisha", "Thin (Krisha)", "પાતળો (કૃશ)", "दुबला (कृश)"),
                ("madhyama", "Medium (Madhyama)", "મધ્યમ", "मध्यम"),
                ("sthula", "Heavy (Sthula)", "ભારે (સ્થૂળ)", "भारी (स्थूल)"),
            )},
            NOTES,
        ],
    },
    # ---------------------------------------------------------------------------------
    {
        "code": "dashavidha",
        "version": 1,
        "kind": "form",
        "name": L("Dashavidha Pariksha", "દશવિધ પરીક્ષા", "दशविध परीक्षा"),
        "description": L("Ten-fold examination", "દસ પ્રકારની પરીક્ષા", "दस प्रकार की परीक्षा"),
        "fields": [
            {"key": "prakriti", "type": "choice", "label": L("Prakriti", "પ્રકૃતિ", "प्रकृति"), "options": DOSHA_TYPES},
            {"key": "vikriti", "type": "multi", "label": L("Vikriti (doshas disturbed now)", "વિકૃતિ (હાલ બગડેલા દોષ)", "विकृति (अभी बिगड़े दोष)"),
             "options": DOSHA_TYPES[:3]},
            {"key": "sara", "type": "choice", "label": L("Sara (tissue quality)", "સાર (ધાતુ ગુણવત્તા)", "सार (धातु गुणवत्ता)"), "options": GRADES},
            {"key": "samhanana", "type": "choice", "label": L("Samhanana (body compactness)", "સંહનન (શરીર બાંધો)", "संहनन (शरीर गठन)"), "options": GRADES},
            {"key": "pramana", "type": "choice", "label": L("Pramana (body proportion)", "પ્રમાણ (શરીર માપ)", "प्रमाण (शरीर अनुपात)"), "options": GRADES},
            {"key": "satmya", "type": "choice", "label": L("Satmya (adaptability)", "સાત્મ્ય (અનુકૂળતા)", "सात्म्य (अनुकूलता)"), "options": GRADES},
            {"key": "satva", "type": "choice", "label": L("Satva (mental strength)", "સત્વ (માનસિક શક્તિ)", "सत्व (मानसिक शक्ति)"), "options": GRADES},
            {"key": "ahara_shakti", "type": "choice", "label": L("Ahara Shakti (eating & digestion capacity)", "આહાર શક્તિ", "आहार शक्ति"), "options": GRADES},
            {"key": "vyayama_shakti", "type": "choice", "label": L("Vyayama Shakti (exercise capacity)", "વ્યાયામ શક્તિ", "व्यायाम शक्ति"), "options": GRADES},
            {"key": "vaya", "type": "choice", "label": L("Vaya (age group)", "વય", "वय"), "options": opts(
                ("bala", "Bala (up to 16)", "બાલ (16 સુધી)", "बाल (16 तक)"),
                ("madhyama", "Madhyama (16-60)", "મધ્યમ (16-60)", "मध्यम (16-60)"),
                ("vriddha", "Vriddha (over 60)", "વૃદ્ધ (60 થી વધુ)", "वृद्ध (60 से अधिक)"),
            )},
            {"key": "bala", "type": "choice", "label": L("Bala (overall strength)", "બળ (શક્તિ)", "बल (शक्ति)"), "options": GRADES},
            NOTES,
        ],
    },
    # ---------------------------------------------------------------------------------
    {
        "code": "agni_habits",
        "version": 1,
        "kind": "form",
        "name": L("Agni & daily habits", "અગ્નિ અને દિનચર્યા", "अग्नि और दिनचर्या"),
        "description": L("Digestion, bowels, sleep, diet and habits", "પાચન, મળ, ઊંઘ, આહાર અને ટેવો", "पाचन, मल, नींद, आहार और आदतें"),
        "fields": [
            {"key": "agni", "type": "choice", "label": L("Agni (digestive fire)", "અગ્નિ (પાચન શક્તિ)", "अग्नि (पाचन शक्ति)"), "options": opts(
                ("sama", "Sama - balanced", "સમ - સંતુલિત", "सम - संतुलित"),
                ("vishama", "Vishama - irregular (Vata)", "વિષમ - અનિયમિત (વાત)", "विषम - अनियमित (वात)"),
                ("tikshna", "Tikshna - sharp (Pitta)", "તીક્ષ્ણ - તેજ (પિત્ત)", "तीक्ष्ण - तेज़ (पित्त)"),
                ("manda", "Manda - slow (Kapha)", "મંદ - ધીમી (કફ)", "मंद - धीमी (कफ)"),
            )},
            {"key": "koshta", "type": "choice", "label": L("Koshta (bowel nature)", "કોષ્ઠ (આંતરડાનો સ્વભાવ)", "कोष्ठ (आंतों का स्वभाव)"), "options": opts(
                ("mridu", "Mridu - soft, easy motions", "મૃદુ - સરળ", "मृदु - आसान"),
                ("madhyama", "Madhyama - medium", "મધ્યમ", "मध्यम"),
                ("krura", "Krura - hard, constipated", "ક્રૂર - કઠણ, કબજિયાત", "क्रूर - सख़्त, कब्ज़"),
            )},
            {"key": "appetite", "type": "choice", "label": L("Appetite", "ભૂખ", "भूख"), "options": opts(
                ("good", "Good", "સારી", "अच्छी"), ("normal", "Normal", "સામાન્ય", "सामान्य"),
                ("poor", "Poor", "ઓછી", "कम"), ("irregular", "Irregular", "અનિયમિત", "अनियमित"),
            )},
            {"key": "thirst", "type": "choice", "label": L("Thirst", "તરસ", "प्यास"), "options": opts(
                ("more", "More", "વધુ", "ज़्यादा"), ("normal", "Normal", "સામાન્ય", "सामान्य"), ("less", "Less", "ઓછી", "कम"),
            )},
            {"key": "sleep", "type": "choice", "label": L("Sleep (Nidra)", "ઊંઘ (નિદ્રા)", "नींद (निद्रा)"), "options": opts(
                ("sound", "Sound", "ગાઢ", "गहरी"), ("disturbed", "Disturbed", "ખલેલવાળી", "बाधित"),
                ("less", "Less", "ઓછી", "कम"), ("excess", "Too much", "વધુ પડતી", "ज़्यादा"),
            )},
            {"key": "sleep_hours", "type": "number", "unit": "h", "min": 0, "max": 24, "label": L("Sleep hours", "ઊંઘના કલાક", "नींद के घंटे")},
            {"key": "bowel_per_day", "type": "number", "unit": "/day", "min": 0, "max": 15, "label": L("Bowel movements", "મળ ત્યાગ", "मल त्याग")},
            {"key": "urine_day", "type": "number", "unit": "/day", "min": 0, "max": 40, "label": L("Urine (day)", "પેશાબ (દિવસ)", "पेशाब (दिन)")},
            {"key": "urine_night", "type": "number", "unit": "/night", "min": 0, "max": 20, "label": L("Urine (night)", "પેશાબ (રાત)", "पेशाब (रात)")},
            {"key": "diet", "type": "choice", "label": L("Diet", "આહાર", "आहार"), "options": opts(
                ("veg", "Vegetarian", "શાકાહારી", "शाकाहारी"), ("jain", "Jain", "જૈન", "जैन"),
                ("egg", "Eggetarian", "ઈંડા સાથે", "अंडा सहित"), ("non_veg", "Non-vegetarian", "માંસાહારી", "मांसाहारी"),
            )},
            {"key": "habits", "type": "multi", "label": L("Habits", "ટેવો", "आदतें"), "options": opts(
                ("tea_coffee", "Tea / coffee 3+ a day", "ચા / કોફી દિવસમાં 3+", "चाय / कॉफ़ी दिन में 3+"),
                ("tobacco", "Tobacco / gutkha", "તમાકુ / ગુટખા", "तंबाकू / गुटखा"),
                ("smoking", "Smoking", "ધૂમ્રપાન", "धूम्रपान"),
                ("alcohol", "Alcohol", "દારૂ", "शराब"),
                ("late_night", "Late nights", "મોડી રાત સુધી જાગવું", "देर रात तक जागना"),
                ("day_sleep", "Day sleep", "દિવસે ઊંઘ", "दिन में सोना"),
                ("junk_food", "Junk / outside food", "બહારનું / જંક ફૂડ", "बाहर का / जंक फ़ूड"),
                ("screen_time", "Long screen time", "લાંબો સ્ક્રીન સમય", "ज़्यादा स्क्रीन समय"),
            )},
            {"key": "exercise", "type": "choice", "label": L("Exercise", "કસરત", "व्यायाम"), "options": opts(
                ("none", "None", "નહીં", "नहीं"), ("light", "Light / walking", "હળવી / ચાલવું", "हल्का / टहलना"),
                ("regular", "Regular", "નિયમિત", "नियमित"),
            )},
            {"key": "stress", "type": "choice", "label": L("Stress", "તણાવ", "तनाव"), "options": opts(
                ("low", "Low", "ઓછો", "कम"), ("medium", "Medium", "મધ્યમ", "मध्यम"), ("high", "High", "વધુ", "ज़्यादा"),
            )},
            NOTES,
        ],
    },
    # ---------------------------------------------------------------------------------
    {
        "code": "prakriti",
        "version": 1,
        "kind": "questionnaire",
        "name": L("Prakriti questionnaire", "પ્રકૃતિ પ્રશ્નાવલી", "प्रकृति प्रश्नावली"),
        "description": L(
            "SAMPLE questions - doctor to review and replace. Each answer counts for Vata, Pitta or Kapha.",
            "નમૂના પ્રશ્નો - ડૉક્ટરે તપાસીને બદલવા. દરેક જવાબ વાત, પિત્ત કે કફમાં ગણાય છે.",
            "नमूना प्रश्न - डॉक्टर जाँचकर बदलें। हर उत्तर वात, पित्त या कफ में गिना जाता है।",
        ),
        "fields": [
            {"key": "frame", "type": "choice", "label": L("Body frame", "શરીરનો બાંધો", "शरीर की बनावट"), "options": opts(
                ("vata", "Thin, light", "પાતળો, હળવો", "पतला, हल्का"),
                ("pitta", "Medium, muscular", "મધ્યમ, સ્નાયુવાળો", "मध्यम, मांसल"),
                ("kapha", "Large, heavy", "મોટો, ભારે", "बड़ा, भारी"),
            )},
            {"key": "weight", "type": "choice", "label": L("Weight", "વજન", "वज़न"), "options": opts(
                ("vata", "Hard to gain", "વધારવું મુશ્કેલ", "बढ़ाना मुश्किल"),
                ("pitta", "Stays steady", "સ્થિર રહે છે", "स्थिर रहता है"),
                ("kapha", "Gains easily", "સહેલાઈથી વધે છે", "आसानी से बढ़ता है"),
            )},
            {"key": "skin", "type": "choice", "label": L("Skin", "ત્વચા", "त्वचा"), "options": opts(
                ("vata", "Dry, rough", "સૂકી, ખરબચડી", "सूखी, खुरदरी"),
                ("pitta", "Warm, oily, gets rashes", "ગરમ, તૈલી, ફોલ્લી થાય", "गर्म, तैलीय, दाने होते हैं"),
                ("kapha", "Thick, smooth, cool", "જાડી, લીસી, ઠંડી", "मोटी, चिकनी, ठंडी"),
            )},
            {"key": "hair", "type": "choice", "label": L("Hair", "વાળ", "बाल"), "options": opts(
                ("vata", "Dry, frizzy", "સૂકા, વાંકડિયા", "सूखे, रूखे"),
                ("pitta", "Thin, early grey or fall", "પાતળા, વહેલા સફેદ કે ખરે", "पतले, जल्दी सफ़ेद या झड़ते"),
                ("kapha", "Thick, oily, wavy", "જાડા, તૈલી, લહેરાતા", "घने, तैलीय, लहरदार"),
            )},
            {"key": "appetite", "type": "choice", "label": L("Appetite", "ભૂખ", "भूख"), "options": opts(
                ("vata", "Irregular", "અનિયમિત", "अनियमित"),
                ("pitta", "Strong, cannot skip meals", "તેજ, ભોજન છોડી ન શકે", "तेज़, भोजन नहीं छोड़ सकते"),
                ("kapha", "Low but steady", "ઓછી પણ સ્થિર", "कम पर स्थिर"),
            )},
            {"key": "bowels", "type": "choice", "label": L("Digestion / bowels", "પાચન / મળ", "पाचन / मल"), "options": opts(
                ("vata", "Gas, constipation", "ગેસ, કબજિયાત", "गैस, कब्ज़"),
                ("pitta", "Loose, frequent", "પાતળો, વારંવાર", "पतला, बार-बार"),
                ("kapha", "Slow, heavy", "ધીમું, ભારે", "धीमा, भारी"),
            )},
            {"key": "sleep", "type": "choice", "label": L("Sleep", "ઊંઘ", "नींद"), "options": opts(
                ("vata", "Light, interrupted", "હળવી, તૂટક", "हल्की, टूटी-फूटी"),
                ("pitta", "Moderate, sound", "મધ્યમ, સારી", "मध्यम, अच्छी"),
                ("kapha", "Deep, long", "ગાઢ, લાંબી", "गहरी, लंबी"),
            )},
            {"key": "weather", "type": "choice", "label": L("Dislikes weather that is", "કેવું હવામાન ન ગમે", "कैसा मौसम पसंद नहीं"), "options": opts(
                ("vata", "Cold and windy", "ઠંડું અને પવનવાળું", "ठंडा और हवादार"),
                ("pitta", "Hot", "ગરમ", "गर्म"),
                ("kapha", "Cold and damp", "ઠંડું અને ભેજવાળું", "ठंडा और नम"),
            )},
            {"key": "sweat", "type": "choice", "label": L("Sweating", "પરસેવો", "पसीना"), "options": opts(
                ("vata", "Little", "ઓછો", "कम"),
                ("pitta", "A lot, strong smell", "વધુ, તીવ્ર ગંધ", "ज़्यादा, तेज़ गंध"),
                ("kapha", "Moderate", "મધ્યમ", "मध्यम"),
            )},
            {"key": "activity", "type": "choice", "label": L("Speech and activity", "બોલવું અને કામ", "बोलचाल और काम"), "options": opts(
                ("vata", "Fast, talkative", "ઝડપી, વાચાળ", "तेज़, बातूनी"),
                ("pitta", "Sharp, to the point", "તીક્ષ્ણ, મુદ્દાસર", "तीखा, सटीक"),
                ("kapha", "Slow, calm", "ધીમું, શાંત", "धीमा, शांत"),
            )},
            {"key": "memory", "type": "choice", "label": L("Learning and memory", "શીખવું અને યાદશક્તિ", "सीखना और याददाश्त"), "options": opts(
                ("vata", "Learns fast, forgets fast", "ઝડપથી શીખે, ઝડપથી ભૂલે", "जल्दी सीखे, जल्दी भूले"),
                ("pitta", "Sharp, clear", "તીક્ષ્ણ, સ્પષ્ટ", "तेज़, स्पष्ट"),
                ("kapha", "Learns slowly, remembers long", "ધીમે શીખે, લાંબું યાદ રાખે", "धीरे सीखे, लंबे समय याद रखे"),
            )},
            {"key": "stress", "type": "choice", "label": L("Under stress becomes", "તણાવમાં થાય છે", "तनाव में होते हैं"), "options": opts(
                ("vata", "Anxious, worried", "ચિંતિત, બેચેન", "चिंतित, बेचैन"),
                ("pitta", "Irritable, angry", "ચીડિયા, ગુસ્સાવાળા", "चिड़चिड़े, गुस्सैल"),
                ("kapha", "Withdrawn, calm", "શાંત, અળગા", "शांत, अलग-थलग"),
            )},
        ],
    },
]
