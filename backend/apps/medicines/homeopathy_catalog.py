"""
SAFE TO EDIT: the homeopathy medicines that "python manage.py add_medicine_catalog" adds (Medicines list, kind
"Homeopathy"). They are shown only when "Homeopathy medicines" is switched on in Additional settings.

!! SAMPLE - pharmacist / homeopath to verify !!  The remedy names are the standard Latin names; the uses, potencies,
pack sizes and prices are examples only (this is NOT the complete Materia Medica, which has thousands of remedies).
Before real use, a qualified homeopath / pharmacist must check the list, or import your own with Medicines -> Import.

Format of each line:  Remedy name | short uses / common names (helps searching)
"""

# ---- Single remedies. Each one is added as a dilution in the potencies given below ----
REMEDIES = """
Aconitum Napellus | Monkshood; sudden fever, fear, anxiety, cold wind, croup
Actaea Spicata | joint pain wrist, rheumatism
Aesculus Hippocastanum | piles, backache, sacrum
Aethusa Cynapium | infant vomiting, milk intolerance
Agaricus Muscarius | twitching, chilblains, cold sensitivity
Agnus Castus | low libido, impotence, lactation
Allium Cepa | onion; hay fever, running cold, sneezing
Aloe Socotrina | piles, diarrhoea, loose stool urgency
Alumina | constipation, dryness, dry skin
Ambra Grisea | nervous cough, shyness
Ammonium Carbonicum | cold, fainting, stout women
Ammonium Muriaticum | sciatica, discharge
Anacardium Orientale | memory, weak digestion, exams
Angustura Vera | stiffness, bone ache
Antimonium Crudum | indigestion, thick coated tongue, warts, corns
Antimonium Tartaricum | bronchitis, rattling cough, children
Apis Mellifica | bee sting; swelling, burning, allergy, urticaria, oedema
Argentum Metallicum | voice, larynx, hoarseness
Argentum Nitricum | exam fear, anxiety, diarrhoea, sugar craving
Arnica Montana | injury, bruise, trauma, muscle soreness, shock
Arsenicum Album | restless, anxiety, food poisoning, asthma, burning
Arsenicum Iodatum | allergic cold, eczema
Arum Triphyllum | sore mouth, cracked lips, hoarseness
Asafoetida | Hing; hysteria, flatulence
Asterias Rubens | breast, cancer pain
Aurum Metallicum | depression, hypertension, bone
Aurum Muriaticum Natronatum | uterus, enlarged organs
Baptisia Tinctoria | typhoid, septic fever, influenza
Baryta Carbonica | delayed growth, tonsils, old age, memory
Baryta Muriatica | hypertension, arteriosclerosis
Belladonna | high fever, sudden pain, red hot face, headache, throbbing
Bellis Perennis | deep injury, sprain, breast injury
Benzoicum Acidum | gout, strong smelling urine
Berberis Vulgaris | kidney stone, renal colic, back pain, urinary
Bismuthum | gastric pain, vomiting
Borax | mouth ulcers, thrush, fear of downward motion
Bovista | menses, bleeding, clumsy
Bromium | croup, hoarseness, sea air
Bryonia Alba | dry cough, joint pain, worse movement, constipation, fever
Bufo Rana | epilepsy, impotence
Cactus Grandiflorus | heart, angina, constriction
Caladium Seguinum | itching, impotence
Calcarea Carbonica | obesity, delayed milestones, teething, cold feet, calcium
Calcarea Fluorica | varicose veins, hard swellings, teeth
Calcarea Phosphorica | growth, bone weakness, anaemia, school children
Calcarea Sulphurica | abscess, pus, eczema
Calendula Officinalis | wound, cut, healing
Camphora | collapse, chill, cold
Cannabis Indica | hallucination, exaggerated time sense
Cannabis Sativa | gonorrhoea, urinary
Cantharis | burns, cystitis, burning urine, blisters
Capsicum Annuum | homesickness, burning
Carbo Animalis | glands, indurated
Carbo Vegetabilis | gas, bloating, collapse, indigestion, old age
Carbolicum Acidum | offensive discharge, ulcer
Carduus Marianus | liver, jaundice, gallstones
Caulophyllum Thalictroides | labour pain, rigid cervix, menses
Causticum | paralysis, hoarseness, burns, warts, bed wetting
Ceanothus Americanus | spleen, pain left
Cedron | periodic fever, neuralgia
Chamomilla | colic, teething, irritable child, toothache, earache
Chelidonium Majus | liver, right shoulder pain, gall bladder
Chenopodium Anthelminticum | worms, ear noise
China Officinalis | weakness, loss of fluid, malaria, gas, anaemia
Chininum Arsenicosum | periodic, weakness
Chininum Sulphuricum | ringing in ears, malaria
Cicuta Virosa | convulsions, spasm
Cimicifuga Racemosa | rheumatism, menses pain, depression, neck
Cina | worms, children, nose picking, grinding teeth
Cinnabaris | sinusitis, eyebrow pain
Cistus Canadensis | glands, cold air sensitivity
Clematis Erecta | testicle, urinary stricture
Coca | altitude sickness, breathlessness
Cocculus Indicus | vertigo, travel sickness, sleeplessness, nursing fatigue
Coccus Cacti | whooping cough
Coffea Cruda | sleeplessness, joyful excitement, toothache
Colchicum Autumnale | gout, nausea at smell of food
Collinsonia Canadensis | piles, constipation, pregnancy piles
Colocynthis | colic, abdominal cramps, sciatica, neuralgia
Conium Maculatum | vertigo, glands, tumour, old age
Corallium Rubrum | whooping cough
Crataegus Oxyacantha | heart tonic, blood pressure
Crocus Sativus | menses dark clots, mood swings
Crotalus Horridus | bleeding, septic
Croton Tiglium | eczema, diarrhoea
Cuprum Metallicum | cramps, convulsions, spasmodic cough
Cyclamen Europaeum | migraine, menses
Digitalis Purpurea | heart, slow pulse
Dioscorea Villosa | colic, bends forward relief
Drosera Rotundifolia | whooping cough, barking cough
Dulcamara | cold damp weather, allergy, warts, diarrhoea
Equisetum Hyemale | bed wetting, bladder
Eupatorium Perfoliatum | dengue, bone pain fever, influenza
Eupatorium Purpureum | kidney, gravel
Euphrasia Officinalis | eye, conjunctivitis, watering eyes
Ferrum Metallicum | anaemia, flushing
Ferrum Phosphoricum | first stage fever, inflammation, nose bleeding
Fluoricum Acidum | bone, hair loss, ulcer
Formica Rufa | rheumatism, gout
Gelsemium Sempervirens | influenza, weakness, anticipation fear, drooping eyelids
Glonoinum | sunstroke, headache, throbbing, hypertension
Graphites | eczema, obesity, constipation, cracked skin, nails
Gratiola | gastric, diarrhoea
Guaiacum | rheumatism, sore throat
Hamamelis Virginica | bleeding, piles, varicose veins, nose bleed
Helleborus Niger | stupor, hydrocephalus
Helonias Dioica | weakness of uterus, protein in urine
Hepar Sulphuris Calcareum | abscess, tonsillitis, croup, pus, cough, boils
Hydrastis Canadensis | thick yellow discharge, mucous membrane, constipation
Hyoscyamus Niger | jealousy, nervous cough, insomnia
Hypericum Perforatum | nerve injury, crushed finger, tetanus prevention
Ignatia Amara | grief, hysteria, disappointment, sighing
Iodum | hyperthyroid, hungry, thin, glands
Ipecacuanha | nausea, vomiting, bleeding, asthma
Iris Versicolor | migraine, vomiting, pancreas
Jaborandi | sweating, salivation
Kali Arsenicosum | skin, psoriasis, asthma
Kali Bichromicum | sinusitis, stringy discharge, ulcer, gastric
Kali Bromatum | sleeplessness, epilepsy, acne
Kali Carbonicum | back pain, weakness, 3 am waking, cough
Kali Iodatum | sinus, syphilis, thick discharge
Kali Muriaticum | white coating tongue, glue ear, swollen glands
Kali Phosphoricum | nervous exhaustion, memory, stress, depression
Kali Sulphuricum | yellow discharge, skin
Kalmia Latifolia | neuralgia, heart, rheumatism
Kreosotum | offensive discharge, teething decay
Lac Caninum | sore throat alternate sides, low self esteem
Lac Defloratum | migraine, constipation
Lachesis Mutus | menopause, left sided, sore throat, jealousy, snake
Latrodectus Mactans | angina, severe pain
Ledum Palustre | puncture wound, insect bite, black eye, gout
Lilium Tigrinum | uterine prolapse, heart, bearing down
Lithium Carbonicum | gout, uric acid
Lobelia Inflata | asthma, nausea
Lycopodium Clavatum | gas, liver, right sided, low confidence, kidney, hair loss
Lyssinum | rabies, hydrophobia
Magnesia Carbonica | acidity, milk intolerance
Magnesia Muriatica | constipation, liver
Magnesia Phosphorica | cramps, colic, neuralgia, menstrual pain
Magnesia Sulphurica | diarrhoea, skin
Mancinella | fear, burning
Medorrhinum | asthma, sycosis, warts
Melilotus | nose bleed, congestion headache
Mercurius Corrosivus | dysentery, ulcers
Mercurius Cyanatus | diphtheria
Mercurius Dulcis | ear, catarrh
Mercurius Iodatus Flavus | throat, right tonsil
Mercurius Iodatus Ruber | throat, left tonsil
Mercurius Solubilis | mouth ulcer, salivation, tonsillitis, sweating, tooth
Mercurius Vivus | ulcers, pus, sweat, tremor
Mezereum | eczema, neuralgia after shingles
Millefolium | bleeding, haemorrhage, bright red
Moschus | hysteria, fainting
Murex Purpurea | uterus, sexual
Muriaticum Acidum | weakness, mouth ulcers, piles
Naja Tripudians | heart, left sided pain
Natrum Arsenicatum | skin, cold
Natrum Carbonicum | weak digestion, sun, milk
Natrum Muriaticum | grief, headache, cold sore, hair fall, depression, salt craving
Natrum Phosphoricum | acidity, sour, gout
Natrum Sulphuricum | asthma, liver, damp, head injury, diarrhoea morning
Nitricum Acidum | ulcers, fissure, warts, splinter pains, piles
Nux Moschata | drowsiness, dryness, flatulence
Nux Vomica | acidity, constipation, hangover, irritability, indigestion, stress
Ocimum Sanctum | Tulsi; cough, fever, immunity
Oleander | skin, scalp
Onosmodium | eye strain, sexual weakness
Opium | constipation no urge, fright, stupor
Origanum | sexual excitement
Oxalicum Acidum | left chest pain, kidney
Paeonia | fissure, ulcer
Palladium | right ovary
Pareira Brava | urinary, prostate
Passiflora Incarnata | insomnia, tension
Petroleum | motion sickness, cracked skin, eczema
Petroselinum | urethra, sudden urge
Phellandrium | cough, pain breast
Phosphoricum Acidum | grief, weakness, hair loss, exams, diabetes
Phosphorus | bleeding, cough, fears, thirst for cold, gastritis
Physostigma | eyes, spasm
Phytolacca Decandra | tonsillitis, breast, mastitis, obesity, sore throat
Picricum Acidum | brain fag, exam, exhaustion
Plantago Major | toothache, ear ache
Platina | pride, nymphomania, sensitivity
Plumbum Metallicum | paralysis, constipation, kidney
Podophyllum Peltatum | diarrhoea, morning, gallbladder
Psorinum | dirty skin, chronic, offensive
Pulsatilla Nigricans | weepy, cold with thick discharge, menses irregular, mild, changeable
Pyrogenium | sepsis, fever
Ranunculus Bulbosus | shingles, herpes, chest wall pain
Raphanus | flatulence after surgery
Ratanhia | fissure, burning, piles
Rheum | sour smell, teething diarrhoea
Rhododendron | joint pain before storm, testicle
Rhus Toxicodendron | joint pain, stiffness better motion, sprain, shingles, chikungunya
Rhus Venenata | skin allergy, vesicles
Robinia | acidity, heartburn
Rumex Crispus | dry cough, tickling, throat pit
Ruta Graveolens | sprain, tendon, eye strain, knee, periosteum
Sabadilla | hay fever, sneezing, worms
Sabal Serrulata | prostate, enlarged
Sabina | uterine bleeding, miscarriage
Sambucus Nigra | child cold, nose blocked, croup
Sanguinaria Canadensis | right shoulder, migraine, polyp
Sanicula Aqua | constipation child, offensive foot sweat
Sarsaparilla | kidney, urinary pain at end
Secale Cornutum | gangrene, bleeding, cold
Selenium | fatigue, hair loss, sexual weakness
Senecio Aureus | menses, urinary, cough
Senega | cough, eyes
Sepia Officinalis | menopause, hormonal, hair fall, pigmentation, bearing down
Silicea | pus, nails, abscess, boils, constipation shy, weak
Spigelia Anthelmia | heart, neuralgia, left sided headache
Spongia Tosta | croup, dry barking cough, thyroid
Stannum Metallicum | weakness, chest, cough
Staphysagria | anger, suppressed, cystitis honeymoon, stye, wound surgery
Sticta Pulmonaria | nose dry, cough, influenza
Stramonium | fear of dark, night terrors, stammering
Sulphur | skin, itching, burning feet, chronic, psoriasis, diarrhoea 5 am
Sulphuricum Acidum | sourness, bruise, stomach
Sumbul | nervous heart
Symphytum Officinale | fracture, bone healing, eye injury
Syphilinum | night pain, ulcer
Tabacum | motion sickness, nausea
Tarentula Hispanica | restlessness, hysteria
Tarentula Cubensis | boils, carbuncle
Terebinthina | kidney, haematuria, burns
Teucrium Marum | worms, nasal polyp
Thlaspi Bursa Pastoris | uterine bleeding
Thuja Occidentalis | warts, vaccination effects, moles, sycosis
Tuberculinum | recurrent infection, wanderlust, chest
Urtica Urens | nettle rash, uric acid, burns, lactation
Ustilago Maydis | uterine bleeding
Valeriana | hysteria, sleeplessness
Veratrum Album | cholera, collapse, cold sweat, diarrhoea vomiting
Veratrum Viride | sunstroke, convulsion
Verbascum Thapsus | facial neuralgia, cough
Viburnum Opulus | dysmenorrhoea, cramps, miscarriage threat
Vinca Minor | scalp, hair
Viola Tricolor | milk scab, eczema children
Vipera | varicose, pain
Xanthoxylum | neuralgia, menses pain
Zincum Metallicum | restless legs, fidgety feet, brain weakness
Zincum Phosphoricum | restless, weakness
Anthracinum | boils, carbuncle
Bacillinum | ringworm, tubercular
Carcinosinum | family history of cancer
Influenzinum | flu prevention
Thyroidinum | thyroid, obesity
Ferrum Picricum | warts, prostate
Hekla Lava | bone, jaw
Kali Nitricum | asthma, kidney
Natrum Nitricum | chest
Ammonium Causticum | cough, sore throat
Antimonium Arsenicosum | emphysema
Apocynum Cannabinum | oedema, ascites
Aranea Diadema | malaria, periodic
Arctium Lappa | skin, kidney
Badiaga | glands, bubo
Blatta Orientalis | asthma
Calcarea Arsenicosa | heart, obesity
Calcarea Iodata | tonsils, adenoids
Chionanthus | liver, jaundice
Cundurango | cancer ulcer, cracks at mouth
Eucalyptus | cough, diabetes, urinary
Gnaphalium | sciatica numbness
Hydrocotyle Asiatica | skin, leprosy, scalp
Iberis Amara | heart palpitation
Juglans Regia | skin, eczema
Kali Chloricum | mouth ulcer
Lemna Minor | nose polyp
Lycopus Virginicus | thyroid, heart
Menyanthes | headache, icy cold
Naphthalinum | asthma, hay fever
Nuphar Luteum | impotence
Pix Liquida | skin, chronic
Polygonum | menses
Rauwolfia Serpentina | hypertension, sleeplessness
Rhamnus Californica | rheumatism
Solidago | kidney, urinary
Tilia | menses
Trillium Pendulum | bleeding
Viscum Album | hypertension, epilepsy
Berberis Aquifolium | skin, acne
Cholesterinum | gall stone, liver
Echinacea Angustifolia | blood poisoning, boils, immunity
Hydrangea | kidney stone, urinary
Gunpowder | septic, boils
Sulphur Iodatum | skin, glands
Scrophularia Nodosa | glands, skin
Cuprum Arsenicosum | cramps
Variolinum | smallpox, chickenpox
Morbillinum | measles
Pertussinum | whooping cough
Tuberculinum Bovinum | recurrent chest infections
Vaccininum | vaccine effects
""".strip().splitlines()

# These are the most used. They are added in 6C, 30C, 200C and 1M. All the others in 30C and 200C.
COMMON = {
    "Aconitum Napellus", "Arnica Montana", "Arsenicum Album", "Belladonna", "Bryonia Alba", "Calcarea Carbonica",
    "Calcarea Phosphorica", "Chamomilla", "China Officinalis", "Gelsemium Sempervirens", "Graphites", "Hepar Sulphuris Calcareum",
    "Ignatia Amara", "Ipecacuanha", "Kali Bichromicum", "Kali Phosphoricum", "Lachesis Mutus", "Ledum Palustre", "Lycopodium Clavatum",
    "Mercurius Solubilis", "Natrum Muriaticum", "Nux Vomica", "Phosphorus", "Pulsatilla Nigricans", "Rhus Toxicodendron", "Ruta Graveolens",
    "Sepia Officinalis", "Silicea", "Staphysagria", "Sulphur", "Thuja Occidentalis", "Apis Mellifica", "Cantharis", "Colocynthis",
    "Magnesia Phosphorica", "Natrum Sulphuricum", "Carbo Vegetabilis", "Cina", "Euphrasia Officinalis", "Hypericum Perforatum",
}

# potency -> (pack, price in Rs). Prices are examples.
DILUTION_POTENCIES = {"6C": ("30 ml", 75), "30C": ("30 ml", 80), "200C": ("30 ml", 95), "1M": ("30 ml", 115)}

# ---- Mother tinctures (Q): name | uses ----
TINCTURES = """
Arnica Montana | bruise, injury
Crataegus Oxyacantha | heart tonic, blood pressure
Ocimum Sanctum | Tulsi; cough, immunity
Carduus Marianus | liver, jaundice
Berberis Vulgaris | kidney stone, urinary
Hydrangea | kidney stone
Justicia Adhatoda | Vasaka; cough, bronchitis
Gymnema Sylvestre | Gurmar; diabetes, sugar
Syzygium Jambolanum | Jamun; diabetes
Cinchona Officinalis | weakness, liver, malaria
Passiflora Incarnata | sleep, anxiety
Avena Sativa | nerve tonic, stress
Withania Somnifera | Ashwagandha; weakness, stress
Rauwolfia Serpentina | hypertension
Terminalia Arjuna | Arjuna; heart
Bacopa Monnieri | Brahmi; memory
Centella Asiatica | Brahmi; skin, memory
Cassia Sophera | skin, eczema
Azadirachta Indica | Neem; skin, blood
Tinospora Cordifolia | Giloy; fever, immunity
Andrographis Paniculata | Kalmegh; liver, fever
Phyllanthus Niruri | Bhumi amla; liver, kidney
Gotu Kola | memory, skin
Aloe Vera | constipation, skin
Calendula Officinalis | wound, cut
Hamamelis Virginica | piles, varicose veins
Aesculus Hippocastanum | piles
Collinsonia Canadensis | piles
Thuja Occidentalis | warts
Echinacea Angustifolia | immunity, boils
Sabal Serrulata | prostate
Solidago Virgaurea | kidney
Hydrocotyle Asiatica | skin
Chelidonium Majus | liver, gall bladder
Taraxacum Officinale | liver, digestion
Fucus Vesiculosus | obesity, thyroid
Phytolacca Decandra | tonsils, obesity
Eupatorium Perfoliatum | fever, body pain
Ruta Graveolens | sprain, eye strain
Symphytum Officinale | fracture, bone
Rhus Toxicodendron | joint pain
Viburnum Opulus | menstrual cramps
Caulophyllum Thalictroides | labour, menses
Cimicifuga Racemosa | menopause, rheumatism
Lycopodium Clavatum | acidity, kidney
Nux Vomica | digestion
Pulsatilla Nigricans | female complaints
Ginkgo Biloba | memory, circulation
Zingiber Officinale | Sunth; digestion, cold
Piper Nigrum | Kali mirch; digestion
Ficus Religiosa | Peepal; diabetes, skin
Acalypha Indica | cough, worms
Abroma Augusta | menses, uterus
Alfalfa | appetite, tonic
Allium Sativum | Garlic; cholesterol, BP
Trigonella Foenum Graecum | Methi; sugar
Momordica Charantia | Karela; diabetes
Santalum Album | Chandan; urinary
Rumex Crispus | dry cough
Senna | constipation
Urtica Urens | urticaria, uric acid
Vitex Negundo | Nirgundi; pain
Boerhaavia Diffusa | Punarnava; oedema, kidney
Tribulus Terrestris | Gokshura; urinary
Eclipta Alba | Bhringraj; hair, liver
Hemidesmus Indicus | Anantmool; skin, blood
Saraca Indica | Ashoka; menses
Holarrhena Antidysenterica | Kutaj; diarrhoea
Curcuma Longa | Haldi; inflammation
Picrorhiza Kurroa | Kutki; liver
""".strip().splitlines()
TINCTURE_PRICE = ("30 ml", 160)
TINCTURE_PRICE_BIG = ("100 ml", 380)

# ---- 12 biochemic tissue salts (Schuessler): name | uses. Tablets in 3X, 6X, 12X, 30X, 200X ----
BIOCHEMIC = """
Calcarea Fluorica | elasticity, varicose veins, cracks, teeth
Calcarea Phosphorica | bones, growth, anaemia, teething
Calcarea Sulphurica | pus, boils, eczema
Ferrum Phosphoricum | first stage fever, inflammation, anaemia
Kali Muriaticum | second stage inflammation, white coating, glands
Kali Phosphoricum | nerves, stress, weakness, depression
Kali Sulphuricum | yellow discharge, skin
Magnesia Phosphorica | cramps, spasm, colic, neuralgia
Natrum Muriaticum | water balance, cold, watery discharge
Natrum Phosphoricum | acidity, indigestion
Natrum Sulphuricum | liver, bile, damp
Silicea | skin, hair, nails, pus
""".strip().splitlines()
BIOCHEMIC_POTENCIES = ["3X", "6X", "12X", "30X", "200X"]
BIOCHEMIC_PRICE = ("25 g", 60)

# ---- Ointments, oils, lotions, ear / eye drops: name | uses | pack | price ----
EXTERNAL = [
    ("Calendula Ointment", "wound, cut, healing, burns", "25 g", 110),
    ("Calendula Lotion", "wound wash, antiseptic", "100 ml", 130),
    ("Arnica Ointment", "bruise, sprain, muscle pain", "25 g", 115),
    ("Arnica Oil", "massage, hair, muscle pain", "100 ml", 150),
    ("Cantharis Ointment", "burns, blisters", "25 g", 110),
    ("Graphites Ointment", "cracks, eczema", "25 g", 110),
    ("Hamamelis Ointment", "piles, varicose veins", "25 g", 115),
    ("Thuja Ointment", "warts, corns", "25 g", 115),
    ("Ruta Oil", "sprain, tendon", "100 ml", 150),
    ("Rhus Tox Ointment", "joint pain, stiffness", "25 g", 115),
    ("Tea Tree Ointment", "fungal skin, acne", "25 g", 120),
    ("Hypericum Lotion", "nerve injury wound", "100 ml", 135),
    ("Euphrasia Eye Drops", "tired eyes, watering, conjunctivitis", "10 ml", 90),
    ("Calendula Ear Drops", "ear infection", "10 ml", 90),
    ("Hair Oil (Jaborandi, Bhringraj)", "hair fall, dandruff", "100 ml", 170),
    ("Rubbing Oil Mixed (Ledum, Ruta, Arnica)", "joint pain massage", "100 ml", 160),
]


def rows():
    """Every medicine of this catalog as a dict (used by services.add_homeopathy_medicines)."""
    out = []
    for line in REMEDIES:
        name, _, uses = (part.strip() for part in line.partition("|"))
        potencies = ["6C", "30C", "200C", "1M"] if name in COMMON else ["30C", "200C"]
        for potency in potencies:
            pack, price = DILUTION_POTENCIES[potency]
            out.append(dict(name=f"{name} {potency}", form="dilution", strength=potency, pack=pack, mrp=price,
                            generic=name, synonyms=f"{name}, {uses}", composition=f"{name} dilution, potency {potency}"))
    for line in TINCTURES:
        name, _, uses = (part.strip() for part in line.partition("|"))
        pack, price = TINCTURE_PRICE
        out.append(dict(name=f"{name} Q", form="mother_tincture", strength="Q", pack=pack, mrp=price, generic=name,
                        synonyms=f"{name} mother tincture, {uses}", composition=f"{name} mother tincture (Q)"))
    for line in BIOCHEMIC:
        name, _, uses = (part.strip() for part in line.partition("|"))
        for potency in BIOCHEMIC_POTENCIES:
            pack, price = BIOCHEMIC_PRICE
            out.append(dict(name=f"{name} {potency} (biochemic)", form="biochemic", strength=potency, pack=pack, mrp=price,
                            generic=name, synonyms=f"{name}, tissue salt, biochemic, {uses}",
                            composition=f"{name} biochemic tablets, potency {potency}"))
    for name, uses, pack, price in EXTERNAL:
        form = "ointment" if "Ointment" in name else "drops" if "Drops" in name else "taila" if "Oil" in name else "other"
        out.append(dict(name=name, form=form,
                        strength="", pack=pack, mrp=price, generic=name, synonyms=f"{name}, {uses}",
                        composition=name, external=True))
    return out
