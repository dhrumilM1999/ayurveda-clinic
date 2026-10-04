"""Functions other modules may call to ask about branches and feature flags."""
from .features_catalog import ADDITIONAL_FEATURES, FEATURES
from .models import BranchFeatureFlag, OrganizationFeature


def organization_features(organization_id) -> dict[str, bool]:
    """
    {code: enabled} of the optional additional features of one organization, including defaults.
    A feature whose "requires" feature is off counts as off.
    """
    saved = dict(OrganizationFeature.objects.filter(organization_id=organization_id).values_list("code", "enabled"))
    values = {code: saved.get(code, info["default"]) for code, info in ADDITIONAL_FEATURES.items()}
    return {code: on and values.get(ADDITIONAL_FEATURES[code].get("requires"), True) for code, on in values.items()}


def branch_features(branch) -> dict[str, bool]:
    """{feature_code: enabled} for one branch: its modules plus the organization's additional features."""
    saved = dict(BranchFeatureFlag.objects.filter(branch=branch).values_list("code", "enabled"))
    values = {code: saved.get(code, info["default"]) for code, info in FEATURES.items()}
    values.update(organization_features(branch.organization_id))
    return values


def is_feature_enabled(branch, code: str) -> bool:
    return branch_features(branch).get(code, False)
