from django.core.management.base import BaseCommand, CommandError

from medstratix.models import GuidelineDocument
from medstratix.services.guideline_structurer import structure_guideline_intelligence


class Command(BaseCommand):
    help = "Creates structured biomarker, testing, and therapy records from extracted guideline sections."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, help="GuidelineDocument ID to process")
        parser.add_argument("--slug", type=str, help="GuidelineDocument slug to process")

    def handle(self, *args, **options):
        guideline = None

        if options["id"]:
            guideline = GuidelineDocument.objects.filter(id=options["id"]).first()
        elif options["slug"]:
            guideline = GuidelineDocument.objects.filter(slug=options["slug"]).first()
        else:
            guideline = GuidelineDocument.objects.order_by("-created_at").first()

        if not guideline:
            raise CommandError("No matching guideline document was found.")

        result = structure_guideline_intelligence(guideline)
        self.stdout.write(
            self.style.SUCCESS(
                "Structuring complete: "
                f"{result['biomarker_definitions_created']} biomarker definitions, "
                f"{result['variant_rules_created']} variant rules, "
                f"{result['testing_rules_created']} testing rules, "
                f"{result['therapy_rules_created']} therapy rules."
            )
        )
