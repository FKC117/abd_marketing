from django.core.management.base import BaseCommand, CommandError

from medstratix.models import GuidelineDocument
from medstratix.services.guideline_extractor import extract_guideline_sections


class Command(BaseCommand):
    help = "Extracts text from a guideline PDF and stores it as GuidelineSection records."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, help="GuidelineDocument ID to process")
        parser.add_argument("--slug", type=str, help="GuidelineDocument slug to process")
        parser.add_argument(
            "--keep-existing",
            action="store_true",
            help="Keep existing sections instead of deleting and rebuilding them",
        )

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

        self.stdout.write(self.style.NOTICE(f"Processing guideline: {guideline.name}"))
        sections = extract_guideline_sections(
            guideline=guideline,
            clear_existing=not options["keep_existing"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Extraction complete. Created {len(sections)} sections for guideline ID {guideline.id}."
            )
        )
