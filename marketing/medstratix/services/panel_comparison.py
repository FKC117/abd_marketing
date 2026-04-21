from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from medstratix.models import (
    AlterationFamily,
    BiomarkerDefinition,
    ComparisonReport,
    GuidelineDocument,
    GuidelineStatus,
    GuidelineTherapyRule,
    MatchType,
    Panel,
    PanelGuidelineGeneMatch,
    PanelGuidelineMatch,
    SampleType,
    TestingMethodRule,
    TestingMethodType,
)

GENE_FAMILY_MEMBERS = {
    "NTRK": {"NTRK1", "NTRK2", "NTRK3", "ETV6-NTRK3"},
    "BRCA": {"BRCA1", "BRCA2"},
    "MMR": {"MLH1", "MSH2", "MSH6", "PMS2"},
}


def _panel_gene_symbols(panel: Panel) -> set[str]:
    return {
        symbol
        for symbol in panel.panel_genes.select_related("gene").values_list("gene__symbol", flat=True)
        if symbol
    }


def _expanded_panel_symbols(panel_symbols: set[str]) -> set[str]:
    expanded = set(panel_symbols)
    reverse_lookup = {}
    for family, members in GENE_FAMILY_MEMBERS.items():
        for member in members:
            reverse_lookup.setdefault(member, set()).add(family)

    for symbol in list(panel_symbols):
        for family in reverse_lookup.get(symbol, set()):
            expanded.add(family)
        if symbol in GENE_FAMILY_MEMBERS:
            expanded.update(GENE_FAMILY_MEMBERS[symbol])
    return expanded


def _percent(numerator: int, denominator: int) -> Decimal:
    if not denominator:
        return Decimal("0.00")
    return (Decimal(numerator) * Decimal("100") / Decimal(denominator)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _guideline_reference_payload(guideline: GuidelineDocument) -> dict:
    definitions = list(
        guideline.biomarker_definitions.select_related("gene").prefetch_related("variant_rules")
    )
    if not definitions:
        return {
            "gene_symbols": set(),
            "definition_by_symbol": {},
        }

    actionable_definitions = [definition for definition in definitions if definition.is_actionable]
    source_definitions = actionable_definitions or definitions
    definition_by_symbol: dict[str, BiomarkerDefinition] = {}
    for definition in source_definitions:
        definition_by_symbol.setdefault(definition.gene.symbol, definition)

    return {
        "gene_symbols": set(definition_by_symbol.keys()),
        "definition_by_symbol": definition_by_symbol,
    }


def _definition_variant_labels(definition: BiomarkerDefinition) -> list[str]:
    labels = [
        label.strip()
        for label in definition.variant_rules.order_by("variant_label").values_list("variant_label", flat=True)
        if label and label.strip()
    ]
    return list(dict.fromkeys(labels))


def _testing_relevance_for(definition: BiomarkerDefinition) -> str:
    methods = list(
        TestingMethodRule.objects.filter(biomarker_definition=definition)
        .order_by("preferred_rank", "method_type")
        .values_list("method_type", flat=True)
        .distinct()
    )
    return ", ".join(methods[:3])


def _therapy_relevance_for(definition: BiomarkerDefinition) -> str:
    therapies = list(
        GuidelineTherapyRule.objects.filter(biomarker_variant_rule__biomarker_definition=definition)
        .select_related("therapy_definition")
        .order_by("therapy_definition__name")
        .values_list("therapy_definition__name", flat=True)
        .distinct()
    )
    return ", ".join(therapies[:4])


def _definition_method_types(definition: BiomarkerDefinition) -> set[str]:
    return {
        method
        for method in TestingMethodRule.objects.filter(biomarker_definition=definition).values_list("method_type", flat=True)
        if method
    }


def _assay_fit_for_definition(panel: Panel, definition: BiomarkerDefinition) -> tuple[str, str]:
    method_types = _definition_method_types(definition)
    alteration_family = definition.alteration_family
    sample_type = panel.sample_type

    if alteration_family == AlterationFamily.FUSION:
        if panel.supports_fusions and (panel.supports_rna_ngs or sample_type == SampleType.TISSUE):
            return "Strong", "Panel explicitly supports fusion detection and has an RNA/tissue-compatible profile."
        if panel.supports_fusions:
            return "Partial", "Panel flags fusion support, but the assay context is not ideal for strong fusion confidence."
        if TestingMethodType.RNA_NGS in method_types:
            return (
                "Strong"
                if sample_type == SampleType.TISSUE
                else "Partial",
                "Fusion-directed biomarker; RNA NGS support is the preferred fit and plasma can underperform.",
            )
        return "Partial", "Fusion biomarker present, but explicit RNA support is not captured in the panel data."

    if alteration_family == AlterationFamily.EXON_SKIPPING:
        if sample_type == SampleType.TISSUE:
            return "Strong", "Exon-skipping event is more credible in tissue-focused profiling."
        return "Partial", "Exon-skipping event may be incompletely characterized in plasma-only workflows."

    if alteration_family in (AlterationFamily.AMPLIFICATION, AlterationFamily.COPY_NUMBER_GAIN):
        if panel.supports_cnv:
            return "Strong", "Panel explicitly supports CNV / amplification detection."
        if TestingMethodType.IHC in method_types or TestingMethodType.FISH in method_types:
            return "Strong", "Copy-number / amplification biomarker aligns with IHC/FISH-linked detection in the guideline."
        return "Partial", "Biomarker is present, but the guideline suggests copy-number or expression confirmation methods."

    if alteration_family == AlterationFamily.PROTEIN_OVEREXPRESSION:
        if panel.supports_ihc:
            return "Strong", "Panel explicitly includes IHC-style companion support for protein-expression biomarkers."
        if TestingMethodType.IHC in method_types:
            return "Strong", "Protein-expression biomarker aligns with IHC-focused detection."
        return "Partial", "Protein-expression marker is present, but explicit IHC-style support is not evident."

    if definition.gene.symbol == "MSI":
        if panel.supports_msi:
            return "Strong", "Panel explicitly supports MSI assessment."
        return "Partial", "Panel includes the biomarker gene context, but MSI support is not explicitly flagged."

    if definition.gene.symbol == "TMB":
        if panel.supports_tmb:
            return "Strong", "Panel explicitly supports TMB estimation."
        return "Partial", "Panel includes the biomarker context, but TMB support is not explicitly flagged."

    if TestingMethodType.PLASMA in method_types and sample_type == SampleType.PLASMA:
        return "Strong", "Panel sample type aligns with plasma-based guideline testing."

    if sample_type == SampleType.PLASMA and TestingMethodType.TISSUE in method_types:
        return "Partial", "Panel is plasma-based while the guideline leans toward tissue testing."

    return "Strong", "Panel sample type and biomarker event class are broadly aligned."


@transaction.atomic
def build_guideline_coverage(panel: Panel) -> dict:
    panel_symbols = _panel_gene_symbols(panel)
    expanded_panel_symbols = _expanded_panel_symbols(panel_symbols)
    guidelines = list(
        GuidelineDocument.objects.filter(status=GuidelineStatus.REVIEWED)
        .prefetch_related("biomarker_definitions__gene", "biomarker_definitions__variant_rules")
        .order_by("cancer_type", "name")
    )

    results = []
    for guideline in guidelines:
        reference = _guideline_reference_payload(guideline)
        guideline_symbols = reference["gene_symbols"]
        if not guideline_symbols:
            continue

        matched_symbols = sorted(symbol for symbol in guideline_symbols if symbol in expanded_panel_symbols)
        missing_symbols = sorted(symbol for symbol in guideline_symbols if symbol not in expanded_panel_symbols)
        coverage_percent = _percent(len(matched_symbols), len(guideline_symbols))
        assay_fit_items = []

        if coverage_percent >= Decimal("80.00"):
            match_status = "Strong"
        elif coverage_percent >= Decimal("50.00"):
            match_status = "Partial"
        else:
            match_status = "Gap"

        match_record, _ = PanelGuidelineMatch.objects.update_or_create(
            panel=panel,
            guideline_document=guideline,
            defaults={
                "cancer_type": guideline.cancer_type,
                "match_status": match_status,
                "matched_genes_count": len(matched_symbols),
                "missing_actionable_genes_count": len(missing_symbols),
                "coverage_percent": coverage_percent,
                "summary_json": {
                    "sample_type": panel.sample_type,
                    "reference_gene_count": len(guideline_symbols),
                    "matched_symbols": matched_symbols,
                    "missing_symbols": missing_symbols[:25],
                },
            },
        )
        match_record.gene_matches.all().delete()

        for symbol in matched_symbols:
            definition = reference["definition_by_symbol"].get(symbol)
            if not definition:
                continue
            assay_fit, assay_note = _assay_fit_for_definition(panel, definition)
            PanelGuidelineGeneMatch.objects.create(
                panel_guideline_match=match_record,
                gene=definition.gene,
                biomarker_definition=definition,
                match_type=MatchType.PRESENT_ACTIONABLE,
                testing_relevance=_testing_relevance_for(definition),
                therapy_relevance=_therapy_relevance_for(definition),
                notes_json={"guideline": guideline.name, "assay_fit": assay_fit, "assay_note": assay_note},
            )
            assay_fit_items.append({"symbol": symbol, "fit": assay_fit, "note": assay_note})

        for symbol in missing_symbols:
            definition = reference["definition_by_symbol"].get(symbol)
            if not definition:
                continue
            PanelGuidelineGeneMatch.objects.create(
                panel_guideline_match=match_record,
                gene=definition.gene,
                biomarker_definition=definition,
                match_type=MatchType.MISSING_ACTIONABLE,
                testing_relevance=_testing_relevance_for(definition),
                therapy_relevance=_therapy_relevance_for(definition),
                notes_json={"guideline": guideline.name, "assay_fit": "Missing", "assay_note": "Biomarker gene is not present in the panel."},
            )

        strong_assay_count = sum(1 for item in assay_fit_items if item["fit"] == "Strong")
        partial_assay_count = sum(1 for item in assay_fit_items if item["fit"] == "Partial")
        results.append(
            {
                "guideline": guideline,
                "coverage_percent": coverage_percent,
                "matched_count": len(matched_symbols),
                "reference_count": len(guideline_symbols),
                "missing_count": len(missing_symbols),
                "matched_symbols": matched_symbols[:12],
                "missing_symbols": missing_symbols[:12],
                "matched_variants": list(
                    dict.fromkeys(
                        label
                        for symbol in matched_symbols
                        for label in _definition_variant_labels(reference["definition_by_symbol"][symbol])
                    )
                )[:12],
                "missing_variants": list(
                    dict.fromkeys(
                        label
                        for symbol in missing_symbols
                        for label in _definition_variant_labels(reference["definition_by_symbol"][symbol])
                    )
                )[:12],
                "match_status": match_status,
                "assay_fit_summary": {
                    "strong": strong_assay_count,
                    "partial": partial_assay_count,
                    "missing": len(missing_symbols),
                },
                "assay_fit_preview": assay_fit_items[:6],
            }
        )

    results.sort(key=lambda item: (-item["coverage_percent"], item["guideline"].cancer_type.lower(), item["guideline"].name.lower()))
    covered_guidelines = [item for item in results if item["matched_count"] > 0]
    gap_guidelines = sorted(
        [item for item in results if item["missing_count"] > 0],
        key=lambda item: (item["coverage_percent"], item["guideline"].cancer_type.lower(), item["guideline"].name.lower()),
    )

    return {
        "panel": panel,
        "average_coverage": _percent(sum(item["matched_count"] for item in results), sum(item["reference_count"] for item in results)) if results else Decimal("0.00"),
        "guideline_count": len(results),
        "covered_guidelines": covered_guidelines,
        "gap_guidelines": gap_guidelines,
        "top_guidelines": results[:6],
        "lowest_guidelines": gap_guidelines[:6],
        "results": results,
    }


@transaction.atomic
def compare_panel_pair(your_panel: Panel, competitor_panel: Panel) -> dict:
    your_symbols = _panel_gene_symbols(your_panel)
    competitor_symbols = _panel_gene_symbols(competitor_panel)

    overlap = sorted(your_symbols & competitor_symbols)
    your_only = sorted(your_symbols - competitor_symbols)
    competitor_only = sorted(competitor_symbols - your_symbols)
    your_coverage = _percent(len(overlap), len(your_symbols))
    competitor_coverage = _percent(len(overlap), len(competitor_symbols))

    price_delta = None
    if your_panel.price is not None and competitor_panel.price is not None:
        price_delta = (your_panel.price - competitor_panel.price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    report_payload = {
        "overlap_symbols": overlap,
        "your_only_symbols": your_only[:30],
        "competitor_only_symbols": competitor_only[:30],
        "sample_type_match": your_panel.sample_type == competitor_panel.sample_type,
        "your_sample_type": your_panel.sample_type,
        "competitor_sample_type": competitor_panel.sample_type,
        "your_coverage_percent": str(your_coverage),
        "competitor_coverage_percent": str(competitor_coverage),
        "price_delta_bdt": str(price_delta) if price_delta is not None else "",
    }
    ComparisonReport.objects.update_or_create(
        panel_a=your_panel,
        panel_b=competitor_panel,
        defaults={
            "overlap_count": len(overlap),
            "unique_a_count": len(your_only),
            "unique_b_count": len(competitor_only),
            "coverage_percent": your_coverage,
            "report_json": report_payload,
        },
    )

    return {
        "competitor_panel": competitor_panel,
        "overlap_count": len(overlap),
        "your_only_count": len(your_only),
        "competitor_only_count": len(competitor_only),
        "overlap_preview": overlap[:12],
        "your_only_preview": your_only[:12],
        "competitor_only_preview": competitor_only[:12],
        "your_coverage_percent": your_coverage,
        "competitor_coverage_percent": competitor_coverage,
        "sample_type_match": your_panel.sample_type == competitor_panel.sample_type,
        "price_delta": price_delta,
    }


def build_comparison_bundle(your_panel: Panel, competitor_panels: list[Panel]) -> dict:
    your_guideline_coverage = build_guideline_coverage(your_panel)
    competitor_comparisons = []
    competitor_guideline_coverages = []

    for competitor_panel in competitor_panels:
        competitor_comparisons.append(compare_panel_pair(your_panel, competitor_panel))
        competitor_guideline_coverages.append(build_guideline_coverage(competitor_panel))

    return {
        "your_panel": your_panel,
        "your_guideline_coverage": your_guideline_coverage,
        "competitor_comparisons": competitor_comparisons,
        "competitor_guideline_coverages": competitor_guideline_coverages,
    }
