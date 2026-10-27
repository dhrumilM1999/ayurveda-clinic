"""
How many whole packs a prescription line needs: dose x times a day x days, divided by what one pack holds
(for example 30 tablets). The same rules as frontend/src/utils/dosage.ts (coursePlan), so the doctor's screen and the
pharmacy counter agree. Returns None when something is missing or the dose unit does not fit the pack (then the
person decides).
"""
import math
import re
from decimal import Decimal

# unit word -> (kind, how many base units one of it is). Base: 1 piece, 1 g, 1 ml.
UNITS = {
    **{w: ("count", 1.0) for w in ("tablet", "tablets", "tab", "capsule", "capsules", "cap", "pill", "pills", "globules",
                                    "vial", "vials", "ampoule", "ampoules", "sachet", "sachets")},
    **{w: ("mass", 1.0) for w in ("g", "gm", "gram", "grams")}, "mg": ("mass", 0.001), "kg": ("mass", 1000.0),
    "ml": ("volume", 1.0), "l": ("volume", 1000.0), "litre": ("volume", 1000.0), "drops": ("volume", 0.05), "drop": ("volume", 0.05),
    "teaspoon": ("volume", 5.0), "tsp": ("volume", 5.0), "tablespoon": ("volume", 15.0), "tbsp": ("volume", 15.0),
}
POWDER_SPOON = {"teaspoon": 3.0, "tsp": 3.0, "tablespoon": 10.0, "tbsp": 10.0}  # a spoon of powder is weighed
DURATION_DAYS = {"days": 1, "weeks": 7, "months": 30}


def _amount(text):
    text = (text or "").strip().replace("½", "1/2")
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)
    frac = re.fullmatch(r"(\d+)/(\d+)", text)
    return int(frac[1]) / int(frac[2]) if frac and int(frac[2]) else None


def doses_per_day(frequency):
    """'1-0-1' -> 2.0; None when it is not a morning-noon-night pattern."""
    parts = (frequency or "").split("-")
    if not 2 <= len(parts) <= 4:
        return None
    total = 0.0
    for part in parts:
        value = _amount(part)
        if value is None:
            return None
        total += value
    return total


def _unit_key(label):
    return re.sub(r"\(.*\)", "", (label or "").lower()).strip().split(" ")[0] if label else ""


def _pack_content(medicine, dose_unit):
    """(amount in base units, kind) of one pack, from pack_size ("60 tablets", "450 ml") or units_per_pack."""
    size = re.match(r"\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)", medicine.pack_size or "")
    if size and size[2].lower() in UNITS:
        kind, factor = UNITS[size[2].lower()]
        return float(size[1]) * factor, kind
    per = medicine.units_per_pack
    if per and Decimal(per) > 0 and UNITS.get(_unit_key(dose_unit), ("", 0))[0] == "count":
        return float(per), "count"
    return None


def packs_needed(item):
    """Whole packs for one PrescriptionItem (a medicine from the list), or None."""
    medicine = item.medicine
    if medicine is None or not item.duration:
        return None
    dose, per_day = _amount(item.dose), doses_per_day(item.frequency)
    unit = UNITS.get(_unit_key(item.dose_unit))
    if dose is None or per_day is None or unit is None:
        return None
    content = _pack_content(medicine, item.dose_unit)
    if content is None:
        return None
    amount, kind = content
    days = item.duration * DURATION_DAYS.get(item.duration_unit, 1)
    factor = unit[1]
    if kind == "mass" and unit[0] == "volume" and _unit_key(item.dose_unit) in POWDER_SPOON:
        factor = POWDER_SPOON[_unit_key(item.dose_unit)]
    elif kind != unit[0]:
        return None
    total = math.ceil(dose * per_day * days * 100) / 100
    return max(1, math.ceil(total * factor / amount - 1e-9))
