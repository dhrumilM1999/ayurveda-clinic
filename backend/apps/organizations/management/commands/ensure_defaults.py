"""
Adds missing starting data for every organization: dropdown values and consent purposes.
Safe to run any time (runs automatically on start). Never changes or removes existing values.

    python manage.py ensure_defaults
"""
from django.core.management.base import BaseCommand

from apps.common.services import ensure_master_values
from apps.organizations.models import Organization
from apps.patients.services import ensure_consent_purposes


def ensure_defaults_for(organization):
    return ensure_master_values(organization), ensure_consent_purposes(organization)


class Command(BaseCommand):
    help = "Add missing dropdown values and consent purposes for every organization."

    def handle(self, *args, **options):
        for org in Organization.objects.all():
            masters, purposes = ensure_defaults_for(org)
            if masters or purposes:
                self.stdout.write(f"{org.name}: added {masters} dropdown values, {purposes} consent purposes.")
