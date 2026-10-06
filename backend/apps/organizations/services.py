"""Functions other modules may call to ask about branches and feature flags."""
from .features_catalog import ADDITIONAL_CHOICES, ADDITIONAL_FEATURES, FEATURES
from .models import BranchFeatureFlag, OrganizationChoice, OrganizationFeature


def organization_features(organization_id) -> dict[str, bool]:
    """
    {code: enabled} of the optional additional features of one organization, including defaults.
    A feature whose "requires" feature is off (directly or further down the chain) counts as off.
    """
    saved = dict(OrganizationFeature.objects.filter(organization_id=organization_id).values_list("code", "enabled"))
    switched = {code: saved.get(code, info["default"]) for code, info in ADDITIONAL_FEATURES.items()}

    def effective(code, seen=()):
        if not switched.get(code) or code in seen:
            return False
        needed = ADDITIONAL_FEATURES[code].get("requires")
        return effective(needed, seen + (code,)) if needed else True

    return {code: effective(code) for code in ADDITIONAL_FEATURES}


def branch_features(branch) -> dict[str, bool]:
    """{feature_code: enabled} for one branch: its modules plus the organization's additional features."""
    saved = dict(BranchFeatureFlag.objects.filter(branch=branch).values_list("code", "enabled"))
    values = {code: saved.get(code, info["default"]) for code, info in FEATURES.items()}
    values.update(organization_features(branch.organization_id))
    return values


def is_feature_enabled(branch, code: str) -> bool:
    return branch_features(branch).get(code, False)


def organization_choices(organization_id) -> dict[str, str]:
    """{code: chosen option} of the organization's additional choices, including defaults."""
    saved = dict(OrganizationChoice.objects.filter(organization_id=organization_id).values_list("code", "value"))
    return {code: saved.get(code, info["default"]) if saved.get(code) in info["options"] else info["default"]
            for code, info in ADDITIONAL_CHOICES.items()}
