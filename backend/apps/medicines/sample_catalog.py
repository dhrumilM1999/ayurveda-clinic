"""
SAFE TO EDIT: SAMPLE medicines added to a new clinic (seed_demo), so the prescription screen can be tried.

!! SAMPLE - pharmacist to verify !!  Names, doses, references, prices and safety flags here are examples
only. Before real use, a qualified Ayurveda pharmacist must check every entry (or import your own list
with Medicines -> Import). The brands at the end are MADE UP.

Each row:
  kind, name, gujarati, hindi, synonyms, dosage form code, composition (short), reference,
  default dose, dose unit code, frequency, timing code, anupana code, MRP, pack size,
  flags: E1 = Schedule E1, M = contains metals/bhasma, P = pregnancy caution, C = child caution
"""

C, PP = "classical", "proprietary"

MEDICINES = [
    (C, "Triphala Churna", "ત્રિફળા ચૂર્ણ", "त्रिफला चूर्ण", "Triphala, Three fruits, ત્રિફલા",
     "churna", "Haritaki, Bibhitaki, Amalaki", "AFI Part I (verify)", "3", "g", "0-0-1", "bedtime", "warm_water",
     90, "100 g", ""),
    (C, "Avipattikar Churna", "અવિપત્તિકર ચૂર્ણ", "अविपत्तिकर चूर्ण", "Avipattikara, acidity churna",
     "churna", "Trikatu, Triphala, Musta, Vidanga, Ela, Patra, Lavanga, Trivrit, Sharkara", "AFI Part I (verify)",
     "3", "g", "1-0-1", "before_food", "water", 95, "100 g", "P"),
    (C, "Hingvashtak Churna", "હિંગ્વાષ્ટક ચૂર્ણ", "हिंग्वाष्टक चूर्ण", "Hingvastaka, Hing churna, Asafoetida",
     "churna", "Hingu, Trikatu, Ajamoda, Saindhava, Jiraka", "AFI Part I (verify)", "2", "g", "1-0-1", "with_food",
     "ghee", 85, "50 g", ""),
    (C, "Sitopaladi Churna", "સિતોપલાદિ ચૂર્ણ", "सितोपलादि चूर्ण", "Sitopaladi, cough churna",
     "churna", "Sharkara, Vamshalochana, Pippali, Ela, Tvak", "AFI Part I (verify)", "2", "g", "1-1-1", "after_food",
     "honey", 110, "50 g", ""),
    (C, "Ashwagandha Churna", "અશ્વગંધા ચૂર્ણ", "अश्वगंधा चूर्ण", "Ashwagandha, Withania, Asgandh",
     "churna", "Ashwagandha root", "API (verify)", "3", "g", "1-0-1", "after_food", "milk", 120, "100 g", ""),
    (C, "Chandraprabha Vati", "ચંદ્રપ્રભા વટી", "चंद्रप्रभा वटी", "Chandraprabha, Chandraprabha Gutika",
     "vati", "Shilajatu, Guggulu, Loha bhasma and herbs", "AFI Part I (verify)", "2", "tablet", "1-0-1",
     "after_food", "warm_water", 140, "60 tablets", "M"),
    (C, "Arogyavardhini Vati", "આરોગ્યવર્ધિની વટી", "आरोग्यवर्धिनी वटी", "Arogyavardhini Rasa, Arogyavardhini Gutika",
     "vati", "Shuddha Parada, Gandhaka, Loha, Abhraka, Tamra bhasma, Kutki", "AFI Part I (verify)", "1", "tablet",
     "1-0-1", "after_food", "warm_water", 150, "60 tablets", "E1,M,P,C"),
    (C, "Sanjivani Vati", "સંજીવની વટી", "संजीवनी वटी", "Sanjivani Gutika",
     "vati", "Vidanga, Shunthi, Pippali, Haritaki, Vatsanabha (Shuddha) and others", "AFI Part I (verify)", "1",
     "tablet", "1-0-1", "after_food", "warm_water", 110, "40 tablets", "E1,P,C"),
    (C, "Kaishore Guggulu", "કૈશોર ગુગ્ગુલુ", "कैशोर गुग्गुलु", "Kaishora Guggulu",
     "guggulu", "Guggulu, Triphala, Guduchi, Trikatu, Vidanga, Trivrit, Danti", "AFI Part I (verify)", "2", "tablet",
     "1-0-1", "after_food", "warm_water", 130, "60 tablets", "P"),
    (C, "Yogaraj Guggulu", "યોગરાજ ગુગ્ગુલુ", "योगराज गुग्गुलु", "Yogaraja Guggulu",
     "guggulu", "Guggulu with Chitraka, Pippali, Triphala and others", "AFI Part I (verify)", "2", "tablet", "1-0-1",
     "after_food", "warm_water", 130, "60 tablets", "P"),
    (C, "Mahayogaraj Guggulu", "મહાયોગરાજ ગુગ્ગુલુ", "महायोगराज गुग्गुलु", "Mahayogaraja Guggulu",
     "guggulu", "Guggulu with Rasa sindura, Loha, Abhraka, Vanga, Naga bhasma and herbs", "AFI Part I (verify)", "1",
     "tablet", "1-0-1", "after_food", "warm_water", 220, "30 tablets", "E1,M,P,C"),
    (C, "Dashamoola Kwatha", "દશમૂલ ક્વાથ", "दशमूल क्वाथ", "Dashamula Kashaya, Dashmool",
     "kashaya", "Ten roots (Bilva, Agnimantha, Shyonaka, Patala, Gambhari, Brihati, Kantakari, Shalaparni...)",
     "AFI Part I (verify)", "15", "ml", "1-0-1", "before_food", "warm_water", 160, "450 ml", ""),
    (C, "Punarnavadi Kashaya", "પુનર્નવાદિ કષાય", "पुनर्नवादि कषाय", "Punarnavadi Kwatha",
     "kashaya", "Punarnava, Nimba, Patola, Shunthi, Guduchi, Daruharidra, Haritaki", "AFI Part I (verify)", "15", "ml",
     "1-0-1", "before_food", "warm_water", 160, "450 ml", ""),
    (C, "Ashokarishta", "અશોકારિષ્ટ", "अशोकारिष्ट", "Ashokarista, Ashoka tonic",
     "arishta", "Ashoka bark, Dhataki, Jiraka, Musta, Shunthi, Amalaki and others", "AFI Part I (verify)", "15",
     "ml", "1-0-1", "after_food", "water", 175, "450 ml", ""),
    (C, "Dashamoolarishta", "દશમૂલારિષ્ટ", "दशमूलारिष्ट", "Dashmularishta",
     "arishta", "Dashamoola, Chitraka, Pushkaramoola, Guduchi and others", "AFI Part I (verify)", "15", "ml", "1-0-1",
     "after_food", "water", 190, "450 ml", ""),
    (C, "Abhayarishta", "અભયારિષ્ટ", "अभयारिष्ट", "Abhayarista, Haritaki arishta",
     "arishta", "Haritaki, Draksha, Vidanga, Madhuka and others", "AFI Part I (verify)", "15", "ml", "0-0-1",
     "after_food", "water", 170, "450 ml", "P"),
    (C, "Kumaryasava", "કુમાર્યાસવ", "कुमार्यासव", "Kumari Asava, Aloe vera asava",
     "asava", "Kumari (Aloe vera) and others", "AFI Part I (verify)", "15", "ml", "1-0-1", "after_food", "water",
     165, "450 ml", "P"),
    (C, "Mahanarayana Taila", "મહાનારાયણ તેલ", "महानारायण तैल", "Mahanarayan oil, Narayana taila",
     "taila", "Bilva, Ashwagandha, Brihati, Shatavari and others in sesame oil", "AFI Part I (verify)", "",
     "apply", "", "", "", 210, "100 ml", ""),
    (C, "Brahmi Ghrita", "બ્રાહ્મી ઘૃત", "ब्राह्मी घृत", "Brahmi ghee, Saraswata ghrita (verify)",
     "ghrita", "Brahmi, Vacha, Kushtha, Shankhapushpi in cow ghee", "AFI Part I (verify)", "5", "g", "1-0-0",
     "empty_stomach", "milk", 240, "200 g", ""),
    (C, "Chyawanprash", "ચ્યવનપ્રાશ", "च्यवनप्राश", "Chyavanaprasha, Chyawanprash Avaleha",
     "lehya", "Amalaki and many herbs, ghee, honey, sugar", "AFI Part I (verify)", "1", "tsp", "1-0-0",
     "empty_stomach", "milk", 260, "500 g", ""),
    # --- MADE-UP sample brands (patent & proprietary) ---
    (PP, "SampleCare Pachak Tablets", "સેમ્પલકેર પાચક ગોળી", "सैम्पलकेयर पाचक गोली", "digestive tablet, pachak",
     "vati", "Sample composition - replace with the label", "", "2", "tablet", "1-0-1", "after_food", "water",
     80, "60 tablets", ""),
    (PP, "SampleCare Joint Oil", "સેમ્પલકેર જોઇન્ટ ઓઇલ", "सैम्पलकेयर जॉइंट ऑयल", "pain oil, joint oil",
     "taila", "Sample composition - replace with the label", "", "", "apply", "", "", "", 150, "100 ml", ""),
    (PP, "SampleCare Triphala Tablets", "સેમ્પલકેર ત્રિફળા ગોળી", "सैम्पलकेयर त्रिफला गोली", "triphala tablet",
     "vati", "Triphala extract 500 mg (sample)", "", "2", "tablet", "0-0-1", "bedtime", "warm_water", 120,
     "60 tablets", ""),
]

# Brand -> classical equivalent (by name)
EQUIVALENTS = {"SampleCare Triphala Tablets": "Triphala Churna"}
