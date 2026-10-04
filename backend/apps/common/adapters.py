"""
Provider adapters: a simple way to swap an external service (SMS, AI, payments...)
by changing one setting in .env. Each service keeps a dictionary of
{"provider name": "python.path.to.Class"} and calls load_provider().
"""
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string


def load_provider(service: str, provider_name: str, registry: dict[str, str]):
    if provider_name not in registry:
        choices = ", ".join(sorted(registry))
        raise ImproperlyConfigured(
            f"Unknown {service} provider '{provider_name}'. Choose one of: {choices}."
        )
    return import_string(registry[provider_name])()
