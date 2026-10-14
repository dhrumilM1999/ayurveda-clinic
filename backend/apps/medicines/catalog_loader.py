"""Adds the bigger medicine catalogs (homeopathy, more generic Ayurveda) to an organization. Safe to run again:
medicines that already exist (same kind and name) are skipped."""
from django.db import transaction

from apps.common.services import ensure_master_values

from .models import Medicine
from .services import MASTER_FIELDS, _master_lookup, save_medicine


def _masters(organization) -> dict:
    ensure_master_values(organization)  # the new dosage forms / units (dilution, pills ...)
    return {field: _master_lookup(organization, cat) for field, cat in MASTER_FIELDS.items()}


def add_homeopathy_medicines(organization) -> int:
    """About 800 homeopathy medicines: remedies in several potencies, mother tinctures, biochemic salts, ointments."""
    from .homeopathy_catalog import rows

    masters = _masters(organization)
    have = set(Medicine.objects.filter(organization=organization, kind="homeopathy").values_list("name", flat=True))
    added = 0
    with transaction.atomic():
        for row in rows():
            if row["name"] in have:
                continue
            potency, form = row["strength"], row["form"]
            external = row.get("external")
            if external:
                dose, unit, freq = "1", "apply", "1-0-1"
                if form == "drops":
                    dose, unit = "2", "drops"
            elif form == "mother_tincture":
                dose, unit, freq = "10", "drops", "1-1-1"
            elif form == "biochemic":
                dose, unit, freq = "4", "tablet", "1-1-1"
            else:  # dilution: low potency more often, high potency once in a while
                dose, unit = "4", "pills"
                freq = "1-1-1" if potency == "6C" else "1-0-1" if potency == "30C" else "1-0-0"
            medicine = Medicine(
                organization=organization, kind="homeopathy", name=row["name"], generic_name=row["generic"],
                synonyms=row["synonyms"], dosage_form=masters["dosage_form"].get(form), composition=row["composition"],
                reference="Homoeopathic Pharmacopoeia of India / Materia Medica (verify)", strength=potency,
                pack_size=row["pack"], mrp=row["mrp"], default_dose=dose, dose_unit=masters["dose_unit"].get(unit),
                default_frequency=freq, default_timing=masters["default_timing"].get("before_food"),
                default_anupana=masters["default_anupana"].get("water") if not external else None,
                hsn_code="3004", gst_rate=12, is_sample=True,
            )
            save_medicine(medicine, None, is_new=True)
            added += 1
    return added


def add_ayurveda_generic_medicines(organization) -> int:
    """About 110 more generic (unbranded) classical Ayurvedic medicines."""
    from .ayurveda_generic_catalog import MEDICINES

    masters = _masters(organization)
    have = set(Medicine.objects.filter(organization=organization, kind="classical").values_list("name", flat=True))
    added = 0
    with transaction.atomic():
        for form, name, syn, comp, dose, unit, freq, timing, anupana, mrp, pack, flags in MEDICINES:
            if name in have:
                continue
            flag_set = {f.strip() for f in flags.split(",") if f.strip()}
            medicine = Medicine(
                organization=organization, kind="classical", name=name, synonyms=syn, generic_name=name,
                dosage_form=masters["dosage_form"].get(form), composition=comp, reference="AFI (verify)",
                default_dose=dose, dose_unit=masters["dose_unit"].get(unit), default_frequency=freq,
                default_timing=masters["default_timing"].get(timing), default_anupana=masters["default_anupana"].get(anupana),
                mrp=mrp, pack_size=pack, hsn_code="3004", gst_rate=12, is_sample=True,
                schedule_e1="E1" in flag_set, contains_metals="M" in flag_set,
                pregnancy_caution="P" in flag_set, child_caution="C" in flag_set,
            )
            save_medicine(medicine, None, is_new=True)
            added += 1
    return added
