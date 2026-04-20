from django.core.management.base import BaseCommand

from medstratix.models import GuidelineDocument
from medstratix.services.guideline_pipeline import process_guideline_document


class Command(BaseCommand):
    help = "Reprocesses guideline records through extraction and structuring after parser or ontology upgrades."

    def add_arguments(self, parser):
        parser.add_argument(
            "--status",
            default="reviewed",
            help="Only reprocess guidelines with this status. Default: reviewed",
        )
        parser.add_argument("--id", type=int, help="Reprocess a single guideline by ID")

    def handle(self, *args, **options):
        if options["id"]:
            guidelines = GuidelineDocument.objects.filter(id=options["id"])
        else:
            guidelines = GuidelineDocument.objects.filter(status=options["status"]).order_by("id")

        processed = 0
        failed = 0

        for guideline in guidelines:
            try:
                result = process_guideline_document(guideline)
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"Failed {guideline.id} {guideline.name}: {exc}"))
                continue

            processed += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processed {guideline.id} {guideline.name}: "
                    f"{result['parser_family']} / {result['molecular_style']} "
                    f"with {result['biomarker_definitions_created']} biomarkers and "
                    f"{result['therapy_rules_created']} therapy rules."
                )
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Reprocess complete. Success: {processed} | Failed: {failed}"))
