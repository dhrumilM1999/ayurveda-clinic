"""
Adds the bigger medicine catalogs to the clinic's Medicines list (safe to run again; nothing is duplicated):
  - about 110 more generic (unbranded) classical Ayurvedic medicines
  - about 800 homeopathy medicines (remedies in potencies, mother tinctures, biochemic salts, ointments)
They are SAMPLE entries (names are standard, prices / packs / uses are examples): a pharmacist must verify them.
Homeopathy shows only when "Homeopathy medicines" is switched on in Additional settings; use --switch-on to do that.

  docker compose exec backend python manage.py add_medicine_catalog --switch-on
"""
from django.core.management.base import BaseCommand

from apps.medicines.catalog_loader import add_ayurveda_generic_medicines, add_homeopathy_medicines
from apps.organizations.models import Organization, OrganizationFeature


class Command(BaseCommand):
    help = "Add the generic Ayurveda and homeopathy medicine catalogs."

    def add_arguments(self, parser):
        parser.add_argument("--switch-on", action="store_true", help="also switch on 'Homeopathy medicines' in Additional settings")
        parser.add_argument("--skip-homeopathy", action="store_true")
        parser.add_argument("--skip-ayurveda", action="store_true")

    def handle(self, *args, **opts):
        for org in Organization.objects.filter(is_deleted=False):
            if not opts["skip_ayurveda"]:
                self.stdout.write(f"{org.name}: {add_ayurveda_generic_medicines(org)} generic Ayurveda medicines added")
            if not opts["skip_homeopathy"]:
                self.stdout.write(f"{org.name}: {add_homeopathy_medicines(org)} homeopathy medicines added")
            if opts["switch_on"]:
                OrganizationFeature.objects.update_or_create(organization=org, code="medicines_homeopathy", defaults={"enabled": True})
                self.stdout.write("Switched on: Homeopathy medicines")
