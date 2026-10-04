"""
SAFE TO EDIT: the starting consent purposes and their wording.

!! SAMPLE TEXT — must be checked by a lawyer (DPDP Act 2023 / DPDP Rules 2025) before real use. !!

These are copied into the database once per organization. To change the wording later,
edit it in the app (the version number goes up so old consents keep the old version).
"""

CONSENT_PURPOSES = [
    {
        "code": "treatment",
        "is_required": True,
        "title": "Treatment and medical records",
        "title_gu": "સારવાર અને તબીબી રેકોર્ડ",
        "title_hi": "इलाज और चिकित्सा रिकॉर्ड",
        "description": (
            "SAMPLE — lawyer to review. I agree that the clinic may collect and keep my personal and "
            "health details to examine me, treat me, prepare bills and keep medical records as required "
            "by law. Only authorised clinic staff can see them."
        ),
        "description_gu": (
            "નમૂનો — વકીલ દ્વારા ચકાસવાનું બાકી. હું સંમતિ આપું છું કે ક્લિનિક મારી તપાસ, સારવાર, બિલ બનાવવા "
            "અને કાયદા મુજબ તબીબી રેકોર્ડ રાખવા માટે મારી વ્યક્તિગત અને આરોગ્ય માહિતી એકત્ર કરી અને રાખી શકે છે. "
            "ફક્ત અધિકૃત ક્લિનિક સ્ટાફ જ તે જોઈ શકે છે."
        ),
        "description_hi": (
            "नमूना — वकील द्वारा जाँच बाकी. मैं सहमति देता/देती हूँ कि क्लिनिक मेरी जाँच, इलाज, बिल बनाने और "
            "कानून के अनुसार चिकित्सा रिकॉर्ड रखने के लिए मेरी व्यक्तिगत और स्वास्थ्य जानकारी एकत्र करके रख सकता है. "
            "केवल अधिकृत क्लिनिक स्टाफ ही इसे देख सकता है."
        ),
    },
    {
        "code": "communication",
        "is_required": False,
        "title": "SMS / WhatsApp messages",
        "title_gu": "SMS / WhatsApp સંદેશા",
        "title_hi": "SMS / WhatsApp संदेश",
        "description": (
            "SAMPLE — lawyer to review. I agree to receive appointment reminders, reports, prescriptions "
            "and follow-up messages by SMS or WhatsApp on my mobile number."
        ),
        "description_gu": (
            "નમૂનો — વકીલ દ્વારા ચકાસવાનું બાકી. હું મારા મોબાઇલ નંબર પર SMS અથવા WhatsApp દ્વારા એપોઇન્ટમેન્ટ "
            "યાદી, રિપોર્ટ, પ્રિસ્ક્રિપ્શન અને ફોલો-અપ સંદેશા મેળવવા સંમત છું."
        ),
        "description_hi": (
            "नमूना — वकील द्वारा जाँच बाकी. मैं अपने मोबाइल नंबर पर SMS या WhatsApp से अपॉइंटमेंट रिमाइंडर, "
            "रिपोर्ट, प्रिस्क्रिप्शन और फॉलो-अप संदेश पाने के लिए सहमत हूँ."
        ),
    },
    {
        "code": "ai_processing",
        "is_required": False,
        "title": "AI assistance for the doctor",
        "title_gu": "ડૉક્ટર માટે AI સહાય",
        "title_hi": "डॉक्टर के लिए AI सहायता",
        "description": (
            "SAMPLE — lawyer to review. I agree that the clinic may use computer AI tools to help the doctor "
            "write notes and summaries. My name, phone and address are removed first. The doctor always "
            "checks and decides. I can say no and still get full treatment."
        ),
        "description_gu": (
            "નમૂનો — વકીલ દ્વારા ચકાસવાનું બાકી. હું સંમતિ આપું છું કે ક્લિનિક ડૉક્ટરને નોંધ અને સારાંશ લખવામાં "
            "મદદ માટે કમ્પ્યુટર AI સાધનો વાપરી શકે છે. પહેલાં મારું નામ, ફોન અને સરનામું દૂર કરવામાં આવે છે. "
            "અંતિમ નિર્ણય હંમેશા ડૉક્ટર લે છે. હું ના પાડું તો પણ મને પૂરી સારવાર મળશે."
        ),
        "description_hi": (
            "नमूना — वकील द्वारा जाँच बाकी. मैं सहमति देता/देती हूँ कि क्लिनिक डॉक्टर को नोट और सारांश लिखने में "
            "मदद के लिए कंप्यूटर AI उपकरण इस्तेमाल कर सकता है. पहले मेरा नाम, फ़ोन और पता हटा दिया जाता है. "
            "अंतिम निर्णय हमेशा डॉक्टर लेते हैं. मैं मना करूँ तब भी मुझे पूरा इलाज मिलेगा."
        ),
    },
    {
        "code": "research",
        "is_required": False,
        "title": "Anonymous research",
        "title_gu": "નામ વગરનું સંશોધન",
        "title_hi": "बिना नाम का शोध",
        "description": (
            "SAMPLE — lawyer to review. I agree that my treatment results may be used for research and "
            "improving care, without my name or any detail that identifies me."
        ),
        "description_gu": (
            "નમૂનો — વકીલ દ્વારા ચકાસવાનું બાકી. હું સંમતિ આપું છું કે મારી સારવારના પરિણામો મારા નામ કે "
            "ઓળખ આપતી કોઈ વિગત વગર સંશોધન અને સારવાર સુધારવા માટે વાપરી શકાય."
        ),
        "description_hi": (
            "नमूना — वकील द्वारा जाँच बाकी. मैं सहमति देता/देती हूँ कि मेरे इलाज के परिणाम मेरे नाम या "
            "पहचान बताने वाली किसी जानकारी के बिना शोध और इलाज सुधारने के लिए उपयोग किए जा सकते हैं."
        ),
    },
]
