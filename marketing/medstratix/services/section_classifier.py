from medstratix.models import SectionType
from medstratix.services.biomarker_ontology import find_biomarkers_in_text


ROLE_KEYWORDS = {
    SectionType.BIOMARKER: (
        "biomarker",
        "molecular",
        "genomic",
        "companion diagnostic",
        "targetable alteration",
        "comprehensive profiling",
        "molecular profiling",
        "somatic testing",
        "germline testing",
    ),
    SectionType.TESTING: (
        "testing",
        "analysis",
        "assay",
        "dna ngs",
        "rna ngs",
        "ihc",
        "fish",
        "plasma",
        "ctdna",
        "sequencing",
        "pathology",
    ),
    SectionType.THERAPY: (
        "therapy",
        "treatment",
        "targeted",
        "systemic therapy",
        "subsequent therapy",
        "first-line",
        "second-line",
        "maintenance",
        "metastatic",
        "recurrent",
    ),
    SectionType.DISCUSSION: (
        "discussion",
        "overview",
        "principles",
        "updates",
        "narrative",
    ),
    SectionType.ALGORITHM: (
        "workup",
        "evaluation",
        "pathway",
        "algorithm",
        "follow-up",
        "surveillance",
    ),
}


def classify_section_type(title: str, section_code: str, text: str) -> str:
    haystack = f"{section_code} {title} {text[:3000]}".lower()
    biomarker_hits = find_biomarkers_in_text(haystack)

    scores = {
        SectionType.BIOMARKER: 0,
        SectionType.TESTING: 0,
        SectionType.THERAPY: 0,
        SectionType.DISCUSSION: 0,
        SectionType.ALGORITHM: 0,
    }

    for section_type, keywords in ROLE_KEYWORDS.items():
        scores[section_type] += sum(1 for keyword in keywords if keyword in haystack)

    if biomarker_hits:
        scores[SectionType.BIOMARKER] += 2 + min(len(biomarker_hits), 4)
        if any(term in haystack for term in ("testing", "analysis", "assay", "profiling", "ihc", "fish", "ngs")):
            scores[SectionType.TESTING] += 2
        if any(term in haystack for term in ("therapy", "treatment", "systemic", "preferred", "subsequent", "maintenance")):
            scores[SectionType.THERAPY] += 2

    if "discussion" in (section_code or "").lower():
        scores[SectionType.DISCUSSION] += 2

    best_type = max(scores, key=scores.get)
    return best_type if scores[best_type] > 0 else SectionType.OTHER
