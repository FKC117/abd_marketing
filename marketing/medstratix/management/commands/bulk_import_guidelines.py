import re
from dataclasses import dataclass
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from pypdf import PdfReader

from medstratix.models import GuidelineDocument, GuidelineStatus
from medstratix.services.guideline_pipeline import process_guideline_document


TITLE_PATTERN = re.compile(
    r"NCCN Clinical Practice Guidelines in Oncology\s*\(NCCN Guidelines(?:[^)]*)\)\s*(.*?)\s+Version\s+([0-9.]+)",
    re.IGNORECASE,
)
COPYRIGHT_YEAR_PATTERN = re.compile(r"[©Â]*\s*(20\d{2})")


@dataclass
class ParsedGuidelineMetadata:
    name: str
    cancer_type: str
    version: str
    year: int | None


def _normalize_spaces(value: str) -> str:
    return " ".join((value or "").split())


def _title_from_stem(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").strip().title()


def _read_first_page_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    if not reader.pages:
        return ""
    return _normalize_spaces(reader.pages[0].extract_text() or "")


def _parse_metadata(pdf_path: Path) -> ParsedGuidelineMetadata:
    first_page = _read_first_page_text(pdf_path)
    fallback_title = _title_from_stem(pdf_path.stem)

    title_match = TITLE_PATTERN.search(first_page)
    if title_match:
        title = _normalize_spaces(title_match.group(1)).strip(" -")
        version = title_match.group(2).strip()
    else:
        title = fallback_title
        version = ""

    year_match = COPYRIGHT_YEAR_PATTERN.search(first_page)
    year = int(year_match.group(1)) if year_match else None

    return ParsedGuidelineMetadata(
        name=title,
        cancer_type=title,
        version=version,
        year=year,
    )


def _existing_guideline_for_file(pdf_path: Path) -> GuidelineDocument | None:
    return GuidelineDocument.objects.filter(source_file__iendswith=pdf_path.name).first()


class Command(BaseCommand):
    help = "Bulk-imports NCCN guideline PDFs from a local folder and optionally processes them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--directory",
            default="medstratix/guidelines",
            help="Directory containing guideline PDFs, relative to the Django project root.",
        )
        parser.add_argument(
            "--skip-processing",
            action="store_true",
            help="Import the files without running extraction and structuring.",
        )
        parser.add_argument(
            "--reprocess-existing",
            action="store_true",
            help="Re-run processing for guideline records that already exist in the database.",
        )

    def handle(self, *args, **options):
        base_dir = Path.cwd()
        directory = Path(options["directory"])
        if not directory.is_absolute():
            directory = base_dir / directory
        directory = directory.resolve()

        if not directory.exists():
            self.stderr.write(self.style.ERROR(f"Directory not found: {directory}"))
            return

        pdf_paths = sorted(directory.glob("*.pdf"))
        if not pdf_paths:
            self.stdout.write(self.style.WARNING(f"No PDF files found in {directory}"))
            return

        process_files = not options["skip_processing"]
        reprocess_existing = options["reprocess_existing"]

        imported_count = 0
        processed_count = 0
        skipped_count = 0
        unsupported_count = 0
        failed_count = 0

        self.stdout.write(self.style.NOTICE(f"Scanning {len(pdf_paths)} PDF files in {directory}"))

        for pdf_path in pdf_paths:
            existing = _existing_guideline_for_file(pdf_path)
            created = False

            if existing and not reprocess_existing:
                skipped_count += 1
                self.stdout.write(f"Skipping existing guideline for {pdf_path.name} (ID {existing.id})")
                continue

            if existing:
                guideline = existing
                self.stdout.write(self.style.NOTICE(f"Reprocessing existing guideline {guideline.id}: {guideline.name}"))
            else:
                metadata = _parse_metadata(pdf_path)
                guideline = GuidelineDocument(
                    name=metadata.name,
                    cancer_type=metadata.cancer_type,
                    version=metadata.version,
                    year=metadata.year,
                    status=GuidelineStatus.IMPORTED,
                )
                with pdf_path.open("rb") as handle:
                    guideline.source_file.save(pdf_path.name, File(handle), save=False)
                guideline.save()
                created = True
                imported_count += 1
                self.stdout.write(self.style.SUCCESS(f"Imported {pdf_path.name} as guideline ID {guideline.id}"))

            if not process_files:
                continue

            try:
                result = process_guideline_document(guideline)
            except ValueError as exc:
                unsupported_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Imported/extracted {pdf_path.name}, but full structuring is not supported yet: {exc}"
                    )
                )
                if created and guideline.status == GuidelineStatus.IMPORTED:
                    guideline.status = GuidelineStatus.EXTRACTED
                    guideline.save(update_fields=["status", "updated_at"])
            except Exception as exc:
                failed_count += 1
                self.stderr.write(self.style.ERROR(f"Failed processing {pdf_path.name}: {exc}"))
            else:
                processed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processed {pdf_path.name}: "
                        f"{result['sections_created']} sections, "
                        f"{result['biomarker_definitions_created']} biomarkers, "
                        f"{result['therapy_rules_created']} therapy rules."
                    )
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Bulk import complete."))
        self.stdout.write(f"Imported new guidelines: {imported_count}")
        self.stdout.write(f"Processed successfully: {processed_count}")
        self.stdout.write(f"Skipped existing: {skipped_count}")
        self.stdout.write(f"Unsupported profiles: {unsupported_count}")
        self.stdout.write(f"Failed: {failed_count}")
