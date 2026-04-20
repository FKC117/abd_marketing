from django.db import transaction

from medstratix.models import (
    BiomarkerDefinition,
    BiomarkerVariantRule,
    Gene,
    GuidelineDocument,
    GuidelineStatus,
    GuidelineTherapyRule,
    MolecularProfile,
    SectionType,
    TestingMethodRule,
    TherapyDefinition,
    TherapyRole,
)
from medstratix.services.biomarker_ontology import find_biomarkers_in_text
from medstratix.services.nccn_profiles import get_parser_profile


def _find_source_section(guideline: GuidelineDocument, aliases: list[str], preferred_codes: tuple[str, ...] = ()) -> object:
    sections = guideline.sections.all()
    lowered_aliases = [alias.lower() for alias in aliases]
    priority_types = {SectionType.BIOMARKER, SectionType.TESTING, SectionType.THERAPY}

    for section in sections:
        haystack = f"{section.section_code} {section.title} {section.normalized_text[:2500]}".lower()
        ontology_hits = find_biomarkers_in_text(haystack)
        if preferred_codes and any(code.lower() in (section.section_code or "").lower() for code in preferred_codes):
            if any(alias in haystack for alias in lowered_aliases):
                return section
            if ontology_hits and section.section_type in priority_types:
                return section

    for section in sections:
        haystack = f"{section.section_code} {section.title} {section.normalized_text[:2500]}".lower()
        ontology_hits = find_biomarkers_in_text(haystack)
        if any(alias in haystack for alias in lowered_aliases) and section.section_type in priority_types:
            return section
        if any(alias in haystack for alias in lowered_aliases):
            return section
        if ontology_hits and section.section_type in priority_types:
            return section

    return guideline.sections.order_by("page_start").first()


def _clear_existing_structured_records(guideline: GuidelineDocument) -> None:
    guideline.therapy_rules.all().delete()
    guideline.testing_method_rules.all().delete()
    guideline.biomarker_variant_rules.all().delete()
    guideline.biomarker_definitions.all().delete()
    guideline.molecular_profiles.all().delete()


@transaction.atomic
def structure_guideline_intelligence(guideline: GuidelineDocument) -> dict:
    section_codes = [section.section_code for section in guideline.sections.exclude(section_code="") if section.section_code]
    profile = get_parser_profile(guideline.name, guideline.cancer_type, section_codes)
    if not profile:
        raise ValueError(
            "No parser profile was matched for this guideline yet. "
            "We need to add a code-family profile for this NCCN document."
        )

    _clear_existing_structured_records(guideline)

    profile_record = MolecularProfile.objects.create(
        guideline_document=guideline,
        cancer_type=guideline.cancer_type,
        name=f"{profile.display_name} - structured biomarkers",
        description=f"Structured biomarker and therapy layer generated from the {profile.code_family} NCCN parser profile.",
        clinical_context=f"{profile.molecular_style} interpretation for {guideline.cancer_type}",
        is_active=True,
    )

    biomarker_definitions_created = 0
    variant_rules_created = 0
    testing_rules_created = 0
    therapy_rules_created = 0
    guideline_context = f"{guideline.name} {guideline.version}".strip()

    for item in profile.catalog:
        gene, _ = Gene.objects.get_or_create(symbol=item.gene)
        source_section = _find_source_section(
            guideline,
            item.aliases,
            preferred_codes=profile.preferred_section_codes,
        )

        biomarker_definition = BiomarkerDefinition.objects.create(
            guideline_document=guideline,
            cancer_type=guideline.cancer_type,
            guideline_context=guideline_context,
            molecular_profile=profile_record,
            gene=gene,
            alias_json=item.aliases,
            alteration_family=item.alteration_family,
            description=item.description,
            is_actionable=item.is_actionable,
            priority_rank=item.priority_rank,
        )
        biomarker_definitions_created += 1

        variant_lookup = {}
        for variant in item.variants:
            variant_rule = BiomarkerVariantRule.objects.create(
                guideline_document=guideline,
                cancer_type=guideline.cancer_type,
                guideline_context=guideline_context,
                biomarker_definition=biomarker_definition,
                variant_label=variant["label"],
                variant_type=variant.get("variant_type", ""),
                testing_context=f"Derived from the {profile.code_family} NCCN parser profile.",
                stage_context=variant.get("stage", ""),
                disease_setting=variant.get("stage", ""),
                line_of_therapy=variant.get("line", ""),
                is_preferred=variant.get("role") == TherapyRole.PREFERRED or variant.get("line", "").lower() == "first-line",
                notes=(source_section.normalized_text[:1000] if source_section else "")[:5000],
                source_section=source_section,
            )
            variant_lookup[variant["label"]] = variant_rule
            variant_rules_created += 1

        for testing_method in item.testing_methods:
            TestingMethodRule.objects.create(
                guideline_document=guideline,
                cancer_type=guideline.cancer_type,
                guideline_context=guideline_context,
                biomarker_definition=biomarker_definition,
                method_type=testing_method["method"],
                preferred_rank=testing_method.get("rank", 0),
                is_required=testing_method.get("required", False),
                notes=testing_method.get("notes", ""),
                source_section=source_section,
            )
            testing_rules_created += 1

        for therapy in item.therapies:
            therapy_definition, _ = TherapyDefinition.objects.get_or_create(name=therapy["name"])
            GuidelineTherapyRule.objects.create(
                guideline_document=guideline,
                cancer_type=guideline.cancer_type,
                guideline_context=guideline_context,
                molecular_profile=profile_record,
                biomarker_variant_rule=variant_lookup[therapy["variant"]],
                therapy_definition=therapy_definition,
                therapy_line=therapy.get("line", ""),
                therapy_role=therapy.get("role", TherapyRole.OTHER),
                patient_context=f"Generated from the {profile.display_name}.",
                stage_context=variant_lookup[therapy["variant"]].stage_context,
                recommendation_strength="Structured starter rule",
                special_notes=(source_section.normalized_text[:1200] if source_section else "")[:5000],
                source_section=source_section,
            )
            therapy_rules_created += 1

    guideline.status = GuidelineStatus.REVIEWED
    guideline.save(update_fields=["status", "updated_at"])

    return {
        "parser_profile": profile.display_name,
        "parser_family": profile.code_family,
        "molecular_style": profile.molecular_style,
        "profile": profile_record,
        "biomarker_definitions_created": biomarker_definitions_created,
        "variant_rules_created": variant_rules_created,
        "testing_rules_created": testing_rules_created,
        "therapy_rules_created": therapy_rules_created,
    }
