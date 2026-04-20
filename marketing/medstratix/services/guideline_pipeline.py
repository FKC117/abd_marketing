from medstratix.models import GuidelineDocument
from medstratix.services.guideline_extractor import extract_guideline_sections
from medstratix.services.guideline_structurer import structure_guideline_intelligence


def process_guideline_document(guideline: GuidelineDocument) -> dict:
    sections = extract_guideline_sections(guideline)
    structured = structure_guideline_intelligence(guideline)
    return {
        "sections_created": len(sections),
        **structured,
    }
