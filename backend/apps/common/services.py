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
