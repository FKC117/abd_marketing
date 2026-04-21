from django.db import transaction

from medstratix.models import (
    AlterationFamily,
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


def _normalize_aliases(*alias_groups) -> list[str]:
    seen = set()
    normalized = []
    for group in alias_groups:
        for alias in group or []:
            value = (alias or "").strip()
            if value:
                key = value.lower()
                if key not in seen:
                    seen.add(key)
                    normalized.append(value)
    return normalized


def _default_variant_label(symbol: str, alteration_family: str, entity_type: str) -> str:
    if entity_type == "fusion" or alteration_family == AlterationFamily.FUSION:
        return symbol if "fusion" in symbol.lower() else f"{symbol} fusion"
    if entity_type == "copy_number":
        return symbol
    if alteration_family == AlterationFamily.AMPLIFICATION:
        return symbol if "amplification" in symbol.lower() else f"{symbol} amplification"
    if alteration_family == AlterationFamily.EXON_SKIPPING:
        return symbol if "exon" in symbol.lower() else f"{symbol} alteration"
    if alteration_family == AlterationFamily.PROTEIN_OVEREXPRESSION:
        if symbol == "CD274":
            return "PD-L1-positive tumor"
        if symbol == "FOLH1":
            return "PSMA-positive disease"
        return symbol if "expression" in symbol.lower() else f"{symbol} expression"
    if entity_type == "genomic_signature":
        return symbol
    if entity_type in {"pathway", "biomarker", "pan_tumor"}:
        return symbol if any(token in symbol.lower() for token in ("score", "burden", "signature", "instability")) else f"{symbol} biomarker"
    return f"{symbol} alteration"


def _default_variant_type(alteration_family: str, entity_type: str) -> str:
    if entity_type == "fusion" or alteration_family == AlterationFamily.FUSION:
        return "fusion"
    if entity_type == "copy_number":
        return "copy_number"
    if alteration_family == AlterationFamily.AMPLIFICATION:
        return "amplification"
    if alteration_family == AlterationFamily.EXON_SKIPPING:
        return "exon_skipping"
    if alteration_family == AlterationFamily.PROTEIN_OVEREXPRESSION:
        return "protein_expression"
    if entity_type == "genomic_signature":
        return "genomic_signature"
    if entity_type in {"pathway", "biomarker", "pan_tumor"}:
        return "biomarker"
    return "mutation"


def _upsert_biomarker_definition(
    guideline: GuidelineDocument,
    profile_record: MolecularProfile,
    guideline_context: str,
    gene_symbol: str,
    alteration_family: str,
    aliases: list[str],
    description: str,
    is_actionable: bool,
    priority_rank: int,
) -> tuple[BiomarkerDefinition, bool]:
    normalized_symbol = (gene_symbol or "").upper().strip()
    gene, _ = Gene.objects.get_or_create(symbol=normalized_symbol)
    biomarker_definition, created = BiomarkerDefinition.objects.get_or_create(
        guideline_document=guideline,
        molecular_profile=profile_record,
        gene=gene,
        alteration_family=alteration_family,
        defaults={
            "cancer_type": guideline.cancer_type,
            "guideline_context": guideline_context,
            "alias_json": aliases,
            "description": description,
            "is_actionable": is_actionable,
            "priority_rank": priority_rank,
        },
    )
    if not created:
        biomarker_definition.cancer_type = guideline.cancer_type
        biomarker_definition.guideline_context = guideline_context
        biomarker_definition.alias_json = _normalize_aliases(biomarker_definition.alias_json, aliases)
        if description:
            if biomarker_definition.description:
                if description not in biomarker_definition.description:
                    biomarker_definition.description = f"{biomarker_definition.description}\n\n{description}"
            else:
                biomarker_definition.description = description
        biomarker_definition.is_actionable = biomarker_definition.is_actionable or is_actionable
        if priority_rank:
            biomarker_definition.priority_rank = min(
                biomarker_definition.priority_rank or priority_rank,
                priority_rank,
            )
        biomarker_definition.save(
            update_fields=[
                "cancer_type",
                "guideline_context",
                "alias_json",
                "description",
                "is_actionable",
                "priority_rank",
                "updated_at",
            ]
        )
    return biomarker_definition, created


def _seed_ontology_biomarkers(
    guideline: GuidelineDocument,
    profile,
    profile_record: MolecularProfile,
    guideline_context: str,
) -> tuple[dict[tuple[str, str], BiomarkerDefinition], int, int]:
    sections = guideline.sections.order_by("page_start", "title")
    relevant_types = {SectionType.BIOMARKER, SectionType.TESTING, SectionType.THERAPY, SectionType.DISCUSSION}
    biomarker_lookup: dict[tuple[str, str], BiomarkerDefinition] = {}
    created_biomarkers = 0
    created_variants = 0

    for section in sections:
        if section.section_type not in relevant_types and not any(
            code.lower() in (section.section_code or "").lower() for code in profile.preferred_section_codes
        ):
            continue

        haystack = f"{section.section_code} {section.title} {section.normalized_text[:5000]}"
        ontology_hits = find_biomarkers_in_text(haystack)
        for rank, entry in enumerate(ontology_hits, start=1):
            key = (entry.canonical_symbol, entry.alteration_family)
            biomarker_definition = biomarker_lookup.get(key)
            if not biomarker_definition:
                biomarker_definition, was_created = _upsert_biomarker_definition(
                    guideline=guideline,
                    profile_record=profile_record,
                    guideline_context=guideline_context,
                    gene_symbol=entry.canonical_symbol,
                    alteration_family=entry.alteration_family,
                    aliases=list(entry.aliases),
                    description=(
                        f"Ontology-derived {entry.entity_type.replace('_', ' ')} match from section "
                        f"{section.section_code or section.title}."
                    ),
                    is_actionable=section.section_type in {SectionType.BIOMARKER, SectionType.THERAPY},
                    priority_rank=100 + rank,
                )
                biomarker_lookup[key] = biomarker_definition
                if was_created:
                    created_biomarkers += 1

                generic_variant_label = _default_variant_label(
                    entry.canonical_symbol,
                    entry.alteration_family,
                    entry.entity_type,
                )
                _, variant_created = BiomarkerVariantRule.objects.get_or_create(
                    guideline_document=guideline,
                    biomarker_definition=biomarker_definition,
                    variant_label=generic_variant_label,
                    defaults={
                        "cancer_type": guideline.cancer_type,
                        "guideline_context": guideline_context,
                        "variant_type": _default_variant_type(entry.alteration_family, entry.entity_type),
                        "testing_context": "Ontology-derived biomarker seed from extracted guideline text.",
                        "disease_setting": guideline.cancer_type,
                        "notes": (section.normalized_text[:1000] if section else "")[:5000],
                        "source_section": section,
                    },
                )
                if variant_created:
                    created_variants += 1

    return biomarker_lookup, created_biomarkers, created_variants


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
    biomarker_lookup, ontology_biomarker_count, ontology_variant_count = _seed_ontology_biomarkers(
        guideline,
        profile,
        profile_record,
        guideline_context,
    )
    biomarker_definitions_created += ontology_biomarker_count
    variant_rules_created += ontology_variant_count

    for item in profile.catalog:
        source_section = _find_source_section(
            guideline,
            item.aliases,
            preferred_codes=profile.preferred_section_codes,
        )

        biomarker_definition, was_created = _upsert_biomarker_definition(
            guideline=guideline,
            profile_record=profile_record,
            guideline_context=guideline_context,
            gene_symbol=item.gene,
            alteration_family=item.alteration_family,
            aliases=item.aliases,
            description=item.description,
            is_actionable=item.is_actionable,
            priority_rank=item.priority_rank,
        )
        biomarker_lookup[(item.gene, item.alteration_family)] = biomarker_definition
        if was_created:
            biomarker_definitions_created += 1

        variant_lookup = {}
        for variant in item.variants:
            variant_rule, created = BiomarkerVariantRule.objects.get_or_create(
                guideline_document=guideline,
                biomarker_definition=biomarker_definition,
                variant_label=variant["label"],
                defaults={
                    "cancer_type": guideline.cancer_type,
                    "guideline_context": guideline_context,
                    "variant_type": variant.get("variant_type", ""),
                    "testing_context": f"Derived from the {profile.code_family} NCCN parser profile.",
                    "stage_context": variant.get("stage", ""),
                    "disease_setting": variant.get("stage", ""),
                    "line_of_therapy": variant.get("line", ""),
                    "is_preferred": variant.get("role") == TherapyRole.PREFERRED or variant.get("line", "").lower() == "first-line",
                    "notes": (source_section.normalized_text[:1000] if source_section else "")[:5000],
                    "source_section": source_section,
                },
            )
            variant_lookup[variant["label"]] = variant_rule
            if not created:
                variant_rule.cancer_type = guideline.cancer_type
                variant_rule.guideline_context = guideline_context
                variant_rule.variant_type = variant.get("variant_type", "") or variant_rule.variant_type
                variant_rule.testing_context = variant_rule.testing_context or f"Derived from the {profile.code_family} NCCN parser profile."
                variant_rule.stage_context = variant.get("stage", "") or variant_rule.stage_context
                variant_rule.disease_setting = variant.get("stage", "") or variant_rule.disease_setting
                variant_rule.line_of_therapy = variant.get("line", "") or variant_rule.line_of_therapy
                variant_rule.is_preferred = (
                    variant_rule.is_preferred
                    or variant.get("role") == TherapyRole.PREFERRED
                    or variant.get("line", "").lower() == "first-line"
                )
                variant_rule.notes = variant_rule.notes or (source_section.normalized_text[:1000] if source_section else "")[:5000]
                if not variant_rule.source_section:
                    variant_rule.source_section = source_section
                variant_rule.save()
            else:
                variant_rules_created += 1

        for testing_method in item.testing_methods:
            _, created = TestingMethodRule.objects.get_or_create(
                guideline_document=guideline,
                biomarker_definition=biomarker_definition,
                method_type=testing_method["method"],
                defaults={
                    "cancer_type": guideline.cancer_type,
                    "guideline_context": guideline_context,
                    "preferred_rank": testing_method.get("rank", 0),
                    "is_required": testing_method.get("required", False),
                    "notes": testing_method.get("notes", ""),
                    "source_section": source_section,
                },
            )
            if created:
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
