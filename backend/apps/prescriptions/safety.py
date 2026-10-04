"""
Prescription safety warnings. These are FIXED RULES written in code (not AI). ASK FIRST before editing.

The doctor always sees the warning and decides; the software never blocks the prescription.
Rules:
  1. Schedule E1 medicine            -> warning (give only on prescription, keep within the advised dose)
  2. Contains metals / bhasma        -> warning (do not use for a long time without monitoring)
  3. Pregnancy caution + the patient is pregnant / breastfeeding (Medical history)  -> DANGER
     Pregnancy caution + woman aged 15-49 (pregnancy not recorded)               -> warning (please confirm)
  4. Child caution + patient under 12 years                                       -> DANGER
  5. Patient's allergy text appears in the medicine name / synonyms / composition -> DANGER
  6. The same medicine twice                                                       -> warning
  7. Long course (over 90 days) of a metal / E1 medicine                          -> warning
"""

DAYS = {"days": 1, "weeks": 7, "months": 30}


def _patient_facts(patient):
    conditions = {c.condition.code for c in patient.conditions.select_related("condition") if c.condition_id}
    allergens = [a.allergen.strip().lower() for a in patient.allergies.all() if a.allergen and len(a.allergen.strip()) >= 3]
    return {
        "age": patient.age_years,
        "female": patient.gender == "female",
        "pregnant": bool(conditions & {"pregnant", "breastfeeding"}),
        "allergens": allergens,
    }


def check_prescription(patient, lines: list[dict]) -> list[dict]:
    """
    lines: [{"medicine": Medicine or None, "medicine_name": str, "duration": int|None, "duration_unit": str}]
    Returns [{"level": "danger"|"warning", "rule": str, "medicine": name, "message": str}].
    """
    facts = _patient_facts(patient)
    warnings = []
    seen = {}

    def add(level, rule, name, message):
        warnings.append({"level": level, "rule": rule, "medicine": name, "message": message})

    for line in lines:
        medicine = line.get("medicine")
        name = line.get("medicine_name") or (medicine.name if medicine else "")
        key = medicine.id if medicine else name.lower()
        if key in seen:
            add("warning", "duplicate", name, "This medicine is written twice.")
        seen[key] = True
        if medicine is None:
            continue

        days = (line.get("duration") or 0) * DAYS.get(line.get("duration_unit") or "days", 1)
        if medicine.schedule_e1:
            add("warning", "schedule_e1", name,
                "Schedule E1 medicine: give only on prescription and keep within the advised dose.")
        if medicine.contains_metals:
            add("warning", "metals", name, "Contains metals / bhasma: avoid long use without monitoring.")
        if (medicine.schedule_e1 or medicine.contains_metals) and days > 90:
            add("warning", "long_course", name, f"Long course ({days} days) of a metal / Schedule E1 medicine.")

        if medicine.pregnancy_caution:
            if facts["pregnant"]:
                add("danger", "pregnancy", name, "Pregnancy caution: the patient is pregnant or breastfeeding.")
            elif facts["female"] and facts["age"] is not None and 15 <= facts["age"] <= 49:
                add("warning", "pregnancy_check", name, "Pregnancy caution: please confirm the patient is not pregnant.")
        if medicine.child_caution and facts["age"] is not None and facts["age"] < 12:
            add("danger", "child", name, f"Child caution: the patient is {facts['age']} years old.")

        text = " ".join([medicine.name, medicine.synonyms, medicine.composition]).lower()
        for allergen in facts["allergens"]:
            if allergen in text:
                add("danger", "allergy", name, f"Patient is allergic to '{allergen}'.")
        if medicine.safety_notes:
            add("warning", "note", name, medicine.safety_notes)

    # Most serious first
    return sorted(warnings, key=lambda w: 0 if w["level"] == "danger" else 1)
