"""Functions other modules may call to ask about branches and feature flags."""
from .features_catalog import FEATURES
from .models import BranchFeatureFlag


def branch_features(branch) -> dict[str, bool]:
    """{feature_code: enabled} for one branch, including defaults."""
    saved = dict(BranchFeatureFlag.objects.filter(branch=branch).values_list("code", "enabled"))
    return {code: saved.get(code, info["default"]) for code, info in FEATURES.items()}


def is_feature_enabled(branch, code: str) -> bool:
    return branch_features(branch).get(code, False)
