"""Functions other modules use for master (dropdown) values."""
from .masters_catalog import DEFAULT_VALUES
from .models import MasterValue


def ensure_master_values(organization) -> int:
    """Add the starting dropdown values that are missing. Returns how many were added."""
    existing = set(
        MasterValue.all_objects.filter(organization=organization).values_list("category", "code")
    )
    new = []
    for category, values in DEFAULT_VALUES.items():
        for order, (code, en, gu, hi) in enumerate(values):
            if (category, code) not in existing:
                new.append(MasterValue(
                    organization=organization, category=category, code=code,
                    label=en, label_gu=gu, label_hi=hi, sort_order=order,
                ))
    MasterValue.objects.bulk_create(new)
    return len(new)


def master_value(organization, category, code):
    return MasterValue.objects.filter(organization=organization, category=category, code=code).first()


def translated_master(organization_id, category: str, label: str, lang: str) -> str:
    """A dropdown word saved in English (e.g. 'After food') in Gujarati / Hindi, if that translation exists.
    Used on print-outs and labels in the patient's language."""
    from .models import MasterValue

    if not label or lang not in ("gu", "hi"):
        return label
    value = MasterValue.objects.filter(organization_id=organization_id, category=category, label=label).first()
    return (getattr(value, f"label_{lang}", "") or label) if value else label
