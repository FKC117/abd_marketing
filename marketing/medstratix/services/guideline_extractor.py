import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from medstratix.models import GuidelineDocument, GuidelineSection, GuidelineStatus
from medstratix.services.section_classifier import classify_section_type


SECTION_CODE_RE = re.compile(r"\b([A-Z]{2,10}-[A-Z0-9]+)\b")
SECTION_PAGE_RE = re.compile(r"\b([A-Z]{2,10}-[A-Z0-9]+)\s+\d+\s+of\s+\d+\b")


@dataclass
class ExtractedSection:
    section_code: str
    title: str
    page_start: int
    page_end: int
    raw_text: str
    normalized_text: str
    section_type: str


def extract_text_by_page(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return pages


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def infer_title(page_text: str, section_code: str) -> str:
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    for idx, line in enumerate(lines):
        if section_code in line:
            candidate = line.replace(section_code, "").strip(" -:\u2013")
            if candidate:
                return candidate[:255]
            if idx + 1 < len(lines):
                next_line = lines[idx + 1].strip(" -:\u2013")
                if next_line:
                    return next_line[:255]

    for line in lines[:8]:
        if len(line) > 8 and line.lower() not in {"nccn guidelines version 5.2026", "non-small cell lung cancer"}:
            return line[:255]
    return section_code or "Untitled Section"


def detect_section_code(page_text: str) -> str:
    page_matches = SECTION_PAGE_RE.findall(page_text)
    if page_matches:
        return page_matches[0]

    code_matches = SECTION_CODE_RE.findall(page_text)
    if code_matches:
        return code_matches[0]

    return ""


def build_sections_from_pages(pages: list[str]) -> list[ExtractedSection]:
    sections: list[ExtractedSection] = []
    current: ExtractedSection | None = None

    for index, raw_page_text in enumerate(pages, start=1):
        normalized_page_text = normalize_text(raw_page_text)
        if not normalized_page_text:
            continue

        section_code = detect_section_code(raw_page_text)
        title = infer_title(raw_page_text, section_code)
        section_type = classify_section_type(title, section_code, normalized_page_text)

        if current and section_code and current.section_code == section_code:
            current.page_end = index
            current.raw_text = f"{current.raw_text}\n\n{raw_page_text.strip()}".strip()
            current.normalized_text = f"{current.normalized_text}\n\n{normalized_page_text}".strip()
            continue

        if current:
            sections.append(current)

        current = ExtractedSection(
            section_code=section_code,
            title=title,
            page_start=index,
            page_end=index,
            raw_text=raw_page_text.strip(),
            normalized_text=normalized_page_text,
            section_type=section_type,
        )

    if current:
        sections.append(current)

    return sections


def extract_guideline_sections(guideline: GuidelineDocument, clear_existing: bool = True) -> list[GuidelineSection]:
    if not guideline.source_file:
        raise ValueError("Guideline document does not have a source file.")

    pdf_path = Path(guideline.source_file.path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Guideline source file not found: {pdf_path}")

    pages = extract_text_by_page(pdf_path)
    extracted_sections = build_sections_from_pages(pages)

    if clear_existing:
        guideline.sections.all().delete()

    created_sections = []
    for section in extracted_sections:
        created_sections.append(
            GuidelineSection.objects.create(
                guideline_document=guideline,
                section_code=section.section_code,
                title=section.title,
                page_start=section.page_start,
                page_end=section.page_end,
                raw_text=section.raw_text,
                normalized_text=section.normalized_text,
                section_type=section.section_type,
            )
        )

    guideline.status = GuidelineStatus.EXTRACTED
    guideline.save(update_fields=["status", "updated_at"])
    return created_sections
