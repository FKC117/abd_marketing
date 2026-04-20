from django.core.management.base import BaseCommand

from medstratix.models import GuidelineDocument
from medstratix.services.section_classifier import classify_section_type


class Command(BaseCommand):
    help = "Reclassifies existing guideline sections using the shared NCCN section-role classifier."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, help="GuidelineDocument ID to process")
        parser.add_argument(
            "--all",
            action="store_true",
            help="Reclassify sections for all guideline documents.",
        )

    def handle(self, *args, **options):
        if options["all"]:
            guidelines = GuidelineDocument.objects.all().order_by("id")
        elif options["id"]:
            guidelines = GuidelineDocument.objects.filter(id=options["id"])
        else:
            guidelines = GuidelineDocument.objects.order_by("-created_at")[:1]

        total_updated = 0
        for guideline in guidelines:
            updated = 0
            for section in guideline.sections.all():
                new_type = classify_section_type(section.title, section.section_code, section.normalized_text or section.raw_text)
                if section.section_type != new_type:
                    section.section_type = new_type
                    section.save(update_fields=["section_type", "updated_at"])
                    updated += 1
            total_updated += updated
            self.stdout.write(f"Guideline {guideline.id}: updated {updated} sections")

        self.stdout.write(self.style.SUCCESS(f"Reclassification complete. Updated {total_updated} sections in total."))
