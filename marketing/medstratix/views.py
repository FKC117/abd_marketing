from collections import defaultdict
from decimal import Decimal
import logging
import time

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views.generic import CreateView
from urllib.parse import urlencode
from .forms import (
    GuidelineUploadForm,
    FinalMarketingReportBuilderForm,
    MarketAccountForm,
    MarketingPlanBuilderForm,
    MarketingPlanSectionEditForm,
    MarketStakeholderForm,
    PanelComparisonSelectForm,
    PanelUploadForm,
    SignInForm,
    SignUpForm,
)
from .models import (
    BiomarkerDefinition,
    BiomarkerVariantRule,
    CompanyType,
    ComparisonRun,
    FinalMarketingReport,
    GuidelineDocument,
    GuidelineTherapyRule,
    LLMGenerationLog,
    MarketAccount,
    MarketingPlan,
    MarketStakeholder,
    Panel,
    SampleType,
    StrategyReport,
    TestingMethodRule,
    TestingMethodType,
)
from .services.guideline_pipeline import process_guideline_document
from .services.gemini_models import list_strategy_models
from .services.marketing_plan_schema import (
    MARKETING_PLAN_STYLE_LABELS,
    marketing_plan_sections,
    stringify_plan_value,
)
from .services.marketing_plan_xlsx_export import build_marketing_plan_xlsx
from .services.nccn_profiles import get_parser_profile
from .services.panel_comparison import build_comparison_bundle, build_guideline_coverage, build_panel_set_profile, compare_panel_profiles
from .services.strategy_exporter import (
    build_comparison_run_docx,
    build_final_marketing_report_docx,
    build_final_marketing_report_pdf,
    build_marketing_plan_csv,
    build_marketing_plan_docx,
    build_marketing_plan_pdf,
    build_strategy_docx,
)
from .services.panel_upload import save_uploaded_panel
from .services.strategy_generator import generate_structured_strategy
from .tasks import generate_marketing_plan_task


logger = logging.getLogger("medstratix.views")


def _json_safe_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, set):
        return sorted(_json_safe_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, Panel):
        return {
            "id": value.pk,
            "name": value.name,
            "company": value.company.name,
            "sample_type": value.get_sample_type_display(),
            "price_bdt": str(value.price) if value.price is not None else "",
            "tat": value.tat or "",
        }
    if isinstance(value, GuidelineDocument):
        return {
            "id": value.pk,
            "name": value.name,
            "cancer_type": value.cancer_type,
        }
    return value


def _marketing_plan_section_overrides(plan: MarketingPlan) -> dict:
    return dict((plan.report_json or {}).get("section_overrides", {}) or {})


def _marketing_plan_display_summary(plan: MarketingPlan) -> str:
    overrides = _marketing_plan_section_overrides(plan)
    payload = plan.plan_json or {}
    return (
        overrides.get("executive_summary_override")
        or payload.get("narrative_summary")
        or plan.executive_summary
        or ("Generation is still pending." if plan.status in {"queued", "running"} else "Not provided.")
    )


def _final_marketing_report_summary(ordered_plans: list[MarketingPlan]) -> str:
    summaries = [_marketing_plan_display_summary(plan) for plan in ordered_plans if _marketing_plan_display_summary(plan)]
    if not summaries:
        return "Combined report built from selected marketing plans."
    if len(summaries) == 1:
        return summaries[0]
    return " ".join(summaries[:3])


def _ordered_marketing_plans(selected_plans: list[MarketingPlan], chronology_mode: str, custom_order: list[int] | None = None) -> list[MarketingPlan]:
    selected_plans = list(selected_plans or [])
    if chronology_mode == "newest_first":
        return sorted(selected_plans, key=lambda plan: plan.created_at, reverse=True)
    if chronology_mode == "plan_ladder":
        style_order = {
            "brief_plan": 1,
            "detailed_plan": 2,
            "launch_plan": 3,
            "growth_plan": 4,
            "account_plan": 5,
        }
        return sorted(selected_plans, key=lambda plan: (style_order.get(plan.output_style, 99), plan.created_at))
    if chronology_mode == "custom_ids":
        order_map = {plan_id: index for index, plan_id in enumerate(custom_order or [])}
        return sorted(selected_plans, key=lambda plan: order_map.get(plan.pk, 9999))
    return sorted(selected_plans, key=lambda plan: plan.created_at)


def _final_marketing_report_payload(ordered_plans: list[MarketingPlan], strategist_note: str = "") -> dict:
    sections = []
    for plan in ordered_plans:
        plan_sections = marketing_plan_sections(plan.output_style, plan.plan_json or {})
        for section in plan_sections:
            value = section["value"]
            if isinstance(value, dict):
                section["count"] = len(value)
            elif isinstance(value, list):
                section["count"] = len(value)
            else:
                section["count"] = 1
        sections.append(
            {
                "plan_id": plan.pk,
                "title": plan.title,
                "output_style": plan.output_style,
                "output_style_label": MARKETING_PLAN_STYLE_LABELS.get(plan.output_style, plan.output_style),
                "created_at": plan.created_at.isoformat(),
                "summary": _marketing_plan_display_summary(plan),
                "sections": plan_sections,
            }
        )
    return {
        "ordered_plans": sections,
        "strategist_note": strategist_note or "",
        "combined_summary": _final_marketing_report_summary(ordered_plans),
    }


def _marketing_plan_context_snapshot(plan: MarketingPlan) -> dict:
    payload = plan.plan_json or {}
    overrides = _marketing_plan_section_overrides(plan)
    return {
        "id": plan.pk,
        "title": plan.title,
        "output_style": plan.output_style,
        "output_style_label": MARKETING_PLAN_STYLE_LABELS.get(plan.output_style, plan.output_style),
        "geography": plan.geography,
        "disease_focus": plan.disease_focus,
        "executive_summary": payload.get("executive_summary", {}),
        "market_research": payload.get("market_research", {}),
        "swot": payload.get("swot", {}),
        "target_audience_personas": payload.get("target_audience_personas", []),
        "unique_value_proposition": payload.get("unique_value_proposition", {}),
        "campaign_plan": payload.get("campaign_plan", []),
        "sales_pitch": payload.get("sales_pitch", {}),
        "recommended_next_steps": payload.get("recommended_next_steps", []),
        "sales_expectation": dict((plan.report_json or {}).get("sales_expectation", {}) or {}),
        "human_section_overrides": overrides,
    }


def _marketing_plan_edit_initial(plan: MarketingPlan) -> dict:
    overrides = _marketing_plan_section_overrides(plan)
    payload = plan.plan_json or {}
    return {
        "executive_summary_override": stringify_plan_value(
            overrides.get("executive_summary_override", payload.get("executive_summary", {}).get("summary", plan.executive_summary or ""))
        ),
        "market_research_override": overrides.get(
            "market_research_override",
            "\n\n".join(
                filter(
                    None,
                    [
                        stringify_plan_value(payload.get("market_research", {}).get("market_landscape", "")),
                        stringify_plan_value(payload.get("market_research", {}).get("competitor_audit", "")),
                        stringify_plan_value(payload.get("market_research", {}).get("key_constraints", "")),
                        stringify_plan_value(payload.get("market_research", {}).get("market_distortion", "")),
                        stringify_plan_value(payload.get("market_research", {}).get("opportunity_map", "")),
                    ],
                )
            ),
        ),
        "swot_override": overrides.get(
            "swot_override",
            "\n".join(
                [
                    f"Strengths: {stringify_plan_value(payload.get('swot', {}).get('strengths', []))}",
                    f"Weaknesses: {stringify_plan_value(payload.get('swot', {}).get('weaknesses', []))}",
                    f"Opportunities: {stringify_plan_value(payload.get('swot', {}).get('opportunities', []))}",
                    f"Threats: {stringify_plan_value(payload.get('swot', {}).get('threats', []))}",
                ]
            ).strip(),
        ),
        "personas_override": overrides.get(
            "personas_override",
            "\n\n".join(
                f"{stringify_plan_value(item.get('persona', 'Persona'))}: role={stringify_plan_value(item.get('role', 'N/A'))}; motivations={stringify_plan_value(item.get('motivations', 'N/A'))}; barriers={stringify_plan_value(item.get('barriers', 'N/A'))}"
                for item in payload.get("target_audience_personas", [])
            ),
        ),
        "uvp_override": overrides.get(
            "uvp_override",
            "\n".join(
                filter(
                    None,
                    [
                        stringify_plan_value(payload.get("unique_value_proposition", {}).get("headline", "")),
                        stringify_plan_value(payload.get("unique_value_proposition", {}).get("proof_points", "")),
                        stringify_plan_value(payload.get("unique_value_proposition", {}).get("why_now", "")),
                    ],
                )
            ),
        ),
        "campaigns_override": overrides.get(
            "campaigns_override",
            "\n\n".join(
                f"{stringify_plan_value(item.get('name', 'Campaign'))}: {stringify_plan_value(item.get('objective', 'N/A'))} | {stringify_plan_value(item.get('message', 'N/A'))}"
                for item in payload.get("campaign_plan", [])
            ),
        ),
        "sales_pitch_override": overrides.get(
            "sales_pitch_override",
            "\n".join(
                filter(
                    None,
                    [
                        stringify_plan_value(payload.get("sales_pitch", {}).get("elevator_pitch", "")),
                        stringify_plan_value(payload.get("sales_pitch", {}).get("clinician_pitch", "")),
                        stringify_plan_value(payload.get("sales_pitch", {}).get("institution_pitch", "")),
                    ],
                )
            ),
        ),
        "next_steps_override": overrides.get(
            "next_steps_override",
            "\n".join(stringify_plan_value(item) for item in payload.get("recommended_next_steps", [])),
        ),
    }


def _marketing_plan_display_sections(plan: MarketingPlan) -> list[dict]:
    sections = marketing_plan_sections(plan.output_style, plan.plan_json or {})
    for section in sections:
        value = section["value"]
        if isinstance(value, dict):
            section["count"] = len(value)
        elif isinstance(value, list):
            section["count"] = len(value)
        else:
            section["count"] = 1
    return sections


def _marketing_plan_highlights(plan: MarketingPlan) -> dict:
    payload = plan.plan_json or {}
    sections = marketing_plan_sections(plan.output_style, payload)
    return {
        "section_count": len(sections),
        "campaign_count": len(payload.get("campaign_plan", []) or payload.get("top_campaigns", []) or payload.get("launch_campaigns", [])),
        "timeline_count": len(
            payload.get("execution_roadmap", [])
            or payload.get("ninety_day_timeline", [])
            or payload.get("quarterly_roadmap", [])
            or payload.get("account_action_plan", [])
        ),
        "revenue_row_count": len(payload.get("revenue_model", []) or payload.get("revenue_potential", [])),
    }


def _editable_rowset(rows: list[dict] | None, field_names: list[str], blank_rows: int = 3) -> list[dict]:
    editable = []
    for row in rows or []:
        editable.append(
            {
                "cells": [
                    {
                        "field": field,
                        "label": field.replace("_", " ").title(),
                        "value": stringify_plan_value(row.get(field, "")),
                    }
                    for field in field_names
                ]
            }
        )
    for _ in range(blank_rows):
        editable.append(
            {
                "cells": [
                    {
                        "field": field,
                        "label": field.replace("_", " ").title(),
                        "value": "",
                    }
                    for field in field_names
                ]
            }
        )
    return editable


def _collect_execution_rows(post_data, prefix: str, field_names: list[str]) -> list[dict]:
    total = int(post_data.get(f"{prefix}_total", "0") or 0)
    rows = []
    for index in range(total):
        row = {
            field: (post_data.get(f"{prefix}_{index}_{field}", "") or "").strip()
            for field in field_names
        }
        if any(value for value in row.values()):
            rows.append(row)
    return rows


def _guideline_depth_label(guideline: GuidelineDocument) -> str:
    biomarker_count = guideline.biomarker_definitions.count()
    therapy_count = guideline.therapy_rules.count()
    testing_count = guideline.testing_method_rules.count()

    if biomarker_count >= 8 or therapy_count >= 10 or testing_count >= 8:
        return "Deep"
    if biomarker_count >= 4 or therapy_count >= 4 or testing_count >= 3:
        return "Starter"
    return "Light"


def _guideline_snapshot(guideline: GuidelineDocument) -> dict:
    sections = guideline.sections.count()
    biomarkers = guideline.biomarker_definitions.count()
    variant_labels = list(
        guideline.biomarker_variant_rules.order_by("variant_label").values_list("variant_label", flat=True).distinct()
    )
    therapies = guideline.therapy_rules.count()
    testing = guideline.testing_method_rules.count()
    parser_profile = get_parser_profile(
        guideline.name,
        guideline.cancer_type,
        [section.section_code for section in guideline.sections.all() if section.section_code],
    )

    return {
        "guideline": guideline,
        "sections": sections,
        "biomarkers": biomarkers,
        "variants": len(variant_labels),
        "variant_preview": variant_labels[:8],
        "variant_overflow": max(len(variant_labels) - 8, 0),
        "therapies": therapies,
        "testing": testing,
        "profile": parser_profile,
        "depth_label": _guideline_depth_label(guideline),
    }


def _query_without_page(request, page_keys: tuple[str, ...] = ("page",)) -> str:
    params = request.GET.copy()
    for key in page_keys:
        params.pop(key, None)
    encoded = params.urlencode()
    return f"&{encoded}" if encoded else ""


def _build_query_string(current_filters: dict, **updates) -> str:
    params = {key: value for key, value in current_filters.items() if value}
    for key, value in updates.items():
        if value in ("", None):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = urlencode(params)
    return f"?{encoded}" if encoded else ""


def _serialize_competitor_ids(panels: list[Panel]) -> str:
    return ",".join(str(panel.pk) for panel in panels)


def _parse_competitor_ids(raw_value: str) -> list[int]:
    values = []
    for token in (raw_value or "").split(","):
        token = token.strip()
        if token.isdigit():
            values.append(int(token))
    return values


def _serialize_panel_ids(panels: list[Panel]) -> str:
    return ",".join(str(panel.pk) for panel in panels)


def _parse_panel_ids(raw_value: str) -> list[int]:
    values = []
    for token in (raw_value or "").split(","):
        token = token.strip()
        if token.isdigit():
            values.append(int(token))
    return values


def _active_filter_chips(filters: dict, base_route: str) -> list[dict]:
    labels = {
        "q": "Search",
        "status": "Status",
        "depth": "Depth",
        "sort": "Sort",
        "owner": "Owner",
        "disease": "Disease",
    }
    chips = []
    for key, value in filters.items():
        if key == "query_suffix" or not value:
            continue
        chips.append(
            {
                "label": labels.get(key, key.title()),
                "value": value,
                "remove_url": f"{base_route}{_build_query_string(filters, **{key: ''})}",
            }
        )
    return chips


def _aggregate_testing_panel(method_type: str) -> dict:
    rows = (
        TestingMethodRule.objects.filter(method_type=method_type)
        .values_list("cancer_type", "biomarker_definition__gene__symbol")
        .distinct()
        .order_by("cancer_type", "biomarker_definition__gene__symbol")
    )
    variant_rows = (
        TestingMethodRule.objects.filter(method_type=method_type)
        .values_list("biomarker_definition__variant_rules__variant_label", flat=True)
        .distinct()
        .order_by("biomarker_definition__variant_rules__variant_label")
    )
    grouped: dict[str, list[str]] = defaultdict(list)

    for cancer_type, gene_symbol in rows:
        disease = (cancer_type or "Unspecified disease").strip()
        symbol = (gene_symbol or "").strip()
        if symbol:
            grouped[disease].append(symbol)

    all_genes = sorted({gene for genes in grouped.values() for gene in genes})
    all_variants = sorted({variant.strip() for variant in variant_rows if variant and variant.strip()})

    diseases = [
        {
            "disease": disease,
            "genes": genes,
            "gene_count": len(genes),
        }
        for disease, genes in grouped.items()
    ]
    diseases.sort(key=lambda item: item["disease"].lower())

    return {
        "diseases": diseases,
        "disease_count": len(diseases),
        "gene_total": sum(item["gene_count"] for item in diseases),
        "unique_genes": all_genes,
        "unique_gene_count": len(all_genes),
        "unique_variants": all_variants,
        "unique_variant_count": len(all_variants),
    }


def _aggregate_therapy_panel() -> dict:
    rows = (
        GuidelineTherapyRule.objects.values_list("cancer_type", "therapy_definition__name")
        .distinct()
        .order_by("cancer_type", "therapy_definition__name")
    )
    grouped: dict[str, list[str]] = defaultdict(list)

    for cancer_type, therapy_name in rows:
        disease = (cancer_type or "Unspecified disease").strip()
        therapy = (therapy_name or "").strip()
        if therapy:
            grouped[disease].append(therapy)

    all_therapies = sorted({therapy for therapies in grouped.values() for therapy in therapies})

    diseases = [
        {
            "disease": disease,
            "therapies": therapies,
            "therapy_count": len(therapies),
        }
        for disease, therapies in grouped.items()
    ]
    diseases.sort(key=lambda item: item["disease"].lower())

    return {
        "diseases": diseases,
        "disease_count": len(diseases),
        "therapy_total": sum(item["therapy_count"] for item in diseases),
        "unique_therapies": all_therapies,
        "unique_therapy_count": len(all_therapies),
    }


def _aggregate_biomarker_catalog(search_query: str = "") -> dict:
    biomarker_qs = BiomarkerDefinition.objects.select_related("gene")
    variant_qs = BiomarkerVariantRule.objects.select_related("biomarker_definition__gene")

    if search_query:
        biomarker_qs = biomarker_qs.filter(
            Q(gene__symbol__icontains=search_query)
            | Q(cancer_type__icontains=search_query)
            | Q(description__icontains=search_query)
        )
        variant_qs = variant_qs.filter(
            Q(variant_label__icontains=search_query)
            | Q(biomarker_definition__gene__symbol__icontains=search_query)
            | Q(cancer_type__icontains=search_query)
        )

    grouped: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"genes": set(), "variants": set()})

    for cancer_type, gene_symbol in biomarker_qs.values_list("cancer_type", "gene__symbol"):
        disease = (cancer_type or "Unspecified disease").strip()
        symbol = (gene_symbol or "").strip()
        if symbol:
            grouped[disease]["genes"].add(symbol)

    for cancer_type, variant_label in variant_qs.values_list("cancer_type", "variant_label"):
        disease = (cancer_type or "Unspecified disease").strip()
        variant = (variant_label or "").strip()
        if variant:
            grouped[disease]["variants"].add(variant)

    diseases = [
        {
            "disease": disease,
            "genes": sorted(payload["genes"]),
            "variants": sorted(payload["variants"]),
            "gene_count": len(payload["genes"]),
            "variant_count": len(payload["variants"]),
        }
        for disease, payload in grouped.items()
    ]
    diseases.sort(key=lambda item: item["disease"].lower())

    unique_genes = sorted({gene for item in diseases for gene in item["genes"]})
    unique_variants = sorted({variant for item in diseases for variant in item["variants"]})

    return {
        "diseases": diseases,
        "disease_count": len(diseases),
        "gene_total": sum(item["gene_count"] for item in diseases),
        "variant_total": sum(item["variant_count"] for item in diseases),
        "unique_genes": unique_genes,
        "unique_gene_count": len(unique_genes),
        "unique_variants": unique_variants,
        "unique_variant_count": len(unique_variants),
    }


def _panel_snapshot(panel: Panel) -> dict:
    gene_symbols = list(panel.panel_genes.select_related("gene").order_by("gene__symbol").values_list("gene__symbol", flat=True))
    capabilities = []
    capability_map = (
        ("supports_dna_ngs", "DNA NGS"),
        ("supports_rna_ngs", "RNA NGS"),
        ("supports_fusions", "Fusion Detection"),
        ("supports_cnv", "CNV"),
        ("supports_msi", "MSI"),
        ("supports_tmb", "TMB"),
        ("supports_ihc", "IHC"),
        ("supports_fish", "FISH"),
    )
    for attr, label in capability_map:
        if getattr(panel, attr, False):
            capabilities.append(label)
    return {
        "panel": panel,
        "gene_count": len(gene_symbols),
        "gene_preview": gene_symbols[:10],
        "gene_overflow": max(len(gene_symbols) - 10, 0),
        "sample_type_label": panel.get_sample_type_display(),
        "capabilities": capabilities,
        "gene_panel_available": panel.gene_panel_available,
        "website_url": panel.website_url,
    }


def _panel_initial(panel: Panel) -> dict:
    gene_text = "\n".join(
        panel.panel_genes.select_related("gene").order_by("gene__symbol").values_list("gene__symbol", flat=True)
    )
    return {
        "company_name": panel.company.name,
        "panel_name": panel.name,
        "website_url": panel.website_url,
        "gene_panel_available": panel.gene_panel_available,
        "sample_type": panel.sample_type,
        "supports_dna_ngs": panel.supports_dna_ngs,
        "supports_rna_ngs": panel.supports_rna_ngs,
        "supports_fusions": panel.supports_fusions,
        "supports_cnv": panel.supports_cnv,
        "supports_msi": panel.supports_msi,
        "supports_tmb": panel.supports_tmb,
        "supports_ihc": panel.supports_ihc,
        "supports_fish": panel.supports_fish,
        "price": panel.price,
        "price_currency": "BDT",
        "tat": panel.tat,
        "gene_text": gene_text,
        "company_type": panel.company.type,
    }


def _market_snapshot(account: MarketAccount) -> dict:
    stakeholders = list(account.stakeholders.order_by("name"))
    return {
        "account": account,
        "stakeholders": stakeholders,
        "stakeholder_count": len(stakeholders),
        "verified_stakeholder_count": sum(1 for stakeholder in stakeholders if stakeholder.is_verified),
    }


def _selected_market_accounts(market_accounts: list[MarketAccount], selected_ids: list[str]) -> list[MarketAccount]:
    selected_id_set = {item.strip() for item in selected_ids if item.strip().isdigit()}
    return [account for account in market_accounts if str(account.pk) in selected_id_set]


def _panel_set_summary(panels: list[Panel]) -> dict:
    profile = build_panel_set_profile(panels) if panels else None
    if not profile:
        return {}
    return {
        "name": profile["name"],
        "panel_count": profile["panel_count"],
        "sample_type": profile["sample_type_label"],
        "price_bdt": profile["price_label"],
        "price_rows": profile.get("price_rows", []),
        "tat": profile["tat_label"],
        "panel_names": [panel.name for panel in profile["panels"]],
    }


def _strategy_export_filename(report: StrategyReport, fmt: str) -> str:
    base = slugify(report.title or f"strategy-{report.pk}") or f"strategy-{report.pk}"
    extension = "docx" if fmt == "docx" else fmt
    return f"{base}.{extension}"


def _comparison_run_export_filename(run: ComparisonRun, fmt: str) -> str:
    base = slugify(run.name or f"comparison-run-{run.pk}") or f"comparison-run-{run.pk}"
    extension = "docx" if fmt == "docx" else fmt
    return f"{base}.{extension}"


def _marketing_plan_export_filename(plan: MarketingPlan, fmt: str) -> str:
    base = slugify(plan.title or f"marketing-plan-{plan.pk}") or f"marketing-plan-{plan.pk}"
    extension = "docx" if fmt == "docx" else fmt
    return f"{base}.{extension}"


def _final_marketing_report_export_filename(report: FinalMarketingReport, fmt: str) -> str:
    base = slugify(report.title or f"final-marketing-report-{report.pk}") or f"final-marketing-report-{report.pk}"
    extension = "docx" if fmt == "docx" else fmt
    return f"{base}.{extension}"


def _strategy_export_payload(report: StrategyReport, latest_log: LLMGenerationLog | None) -> dict:
    return {
        "id": report.pk,
        "title": report.title,
        "disease_focus": report.disease_focus,
        "status": report.status,
        "your_panel": {
            "name": report.your_panel.name,
            "company": report.your_panel.company.name,
            "sample_type": report.your_panel.get_sample_type_display(),
            "price_bdt": str(report.your_panel.price) if report.your_panel.price is not None else "",
            "tat": report.your_panel.tat,
        },
        "competitor_panel": {
            "name": report.competitor_panel.name,
            "company": report.competitor_panel.company.name,
            "sample_type": report.competitor_panel.get_sample_type_display(),
            "price_bdt": str(report.competitor_panel.price) if report.competitor_panel.price is not None else "",
            "tat": report.competitor_panel.tat,
        },
        "your_panels": report.report_json.get("your_panels", []),
        "competitor_panels": report.report_json.get("competitor_panels", []),
        "market_accounts": report.report_json.get("market_accounts", []),
        "strategist_note": report.report_json.get("strategist_note", ""),
        "primary_market_account": report.market_account.name if report.market_account else "",
        "executive_summary": report.executive_summary,
        "swot": report.swot_json,
        "market_gap": report.market_gap_json,
        "guideline_coverage_and_advantages": report.guideline_advantages_json,
        "marketing_campaigns": report.campaigns_json,
        "sales_pitch": report.sales_pitch_text,
        "recommended_next_steps": report.report_json.get("recommended_next_steps", []),
        "llm_audit": {
            "provider": report.llm_provider,
            "model": report.llm_model,
            "prompt_tokens": latest_log.prompt_tokens if latest_log else 0,
            "response_tokens": latest_log.response_tokens if latest_log else 0,
            "total_tokens": latest_log.total_tokens if latest_log else 0,
            "estimated_cost_usd": str(latest_log.estimated_cost_usd) if latest_log else "0",
        },
        "created_at": report.created_at.isoformat(),
        "updated_at": report.updated_at.isoformat(),
    }


def _strategy_export_text(payload: dict) -> str:
    lines = [
        payload.get("title") or "Untitled Strategy Report",
        "=" * 72,
        "",
        f"Disease Focus: {payload.get('disease_focus') or 'All diseases'}",
        f"Status: {payload.get('status') or 'N/A'}",
        "",
        "Your Panel",
        f"- Company: {payload['your_panel']['company']}",
        f"- Name: {payload['your_panel']['name']}",
        f"- Sample Type: {payload['your_panel']['sample_type']}",
        f"- Price BDT: {payload['your_panel']['price_bdt'] or 'N/A'}",
        f"- TAT: {payload['your_panel']['tat'] or 'N/A'}",
        "",
        "Your Panel Set",
        "",
        "Competitor Panel",
        f"- Company: {payload['competitor_panel']['company']}",
        f"- Name: {payload['competitor_panel']['name']}",
        f"- Sample Type: {payload['competitor_panel']['sample_type']}",
        f"- Price BDT: {payload['competitor_panel']['price_bdt'] or 'N/A'}",
        f"- TAT: {payload['competitor_panel']['tat'] or 'N/A'}",
        "",
        "Competitor Panel Set",
        "",
        "Market Accounts",
    ]
    your_panels = payload.get("your_panels") or []
    if your_panels:
        for panel in your_panels:
            lines.append(f"- {panel.get('company', 'Unknown')} | {panel.get('name', 'Unknown')} | {panel.get('sample_type', 'N/A')}")
    else:
        lines.append("- None")
    lines.append("")
    competitor_panels = payload.get("competitor_panels") or []
    if competitor_panels:
        for panel in competitor_panels:
            lines.append(f"- {panel.get('company', 'Unknown')} | {panel.get('name', 'Unknown')} | {panel.get('sample_type', 'N/A')}")
    else:
        lines.append("- None")
    lines.append("")
    market_accounts = payload.get("market_accounts") or []
    if market_accounts:
        for account in market_accounts:
            lines.append(f"- {account.get('name', 'Unknown')}{' | ' + account.get('city') if account.get('city') else ''}")
    else:
        lines.append("- None linked")

    lines.extend(
        [
            "",
            "Executive Summary",
            payload.get("executive_summary") or "N/A",
            "",
            "SWOT",
        ]
    )
    for key in ("strengths", "weaknesses", "opportunities", "threats"):
        lines.append(f"{key.title()}:")
        values = payload.get("swot", {}).get(key, []) or []
        if values:
            lines.extend(f"- {item}" for item in values)
        else:
            lines.append("- None")
        lines.append("")

    lines.extend(
        [
            "Market Gap",
            f"- Unmet Need: {payload.get('market_gap', {}).get('unmet_need', 'N/A')}",
            f"- Competitor Gap: {payload.get('market_gap', {}).get('competitor_gap', 'N/A')}",
            f"- Your Gap: {payload.get('market_gap', {}).get('your_gap', 'N/A')}",
            f"- Positioning Space: {payload.get('market_gap', {}).get('positioning_space', 'N/A')}",
            "",
            "Guideline Coverage And Advantages",
        ]
    )
    for key in ("your_advantages", "competitor_advantages", "clinical_watchouts"):
        lines.append(f"{key.replace('_', ' ').title()}:")
        values = payload.get("guideline_coverage_and_advantages", {}).get(key, []) or []
        if values:
            lines.extend(f"- {item}" for item in values)
        else:
            lines.append("- None")
        lines.append("")

    lines.append("Marketing Campaigns")
    campaigns = payload.get("marketing_campaigns", []) or []
    if campaigns:
        for index, campaign in enumerate(campaigns, start=1):
            lines.extend(
                [
                    f"{index}. {campaign.get('name', 'Untitled Campaign')}",
                    f"   Audience: {campaign.get('audience', 'N/A')}",
                    f"   Message: {campaign.get('message', 'N/A')}",
                    f"   Channel Mix: {campaign.get('channel_mix', 'N/A')}",
                    f"   Proof Point: {campaign.get('proof_point', 'N/A')}",
                    f"   Call To Action: {campaign.get('call_to_action', 'N/A')}",
                    "",
                ]
            )
    else:
        lines.extend(["- None", ""])

    lines.extend(
        [
            "Sales Pitch",
            payload.get("sales_pitch") or "N/A",
            "",
            "Recommended Next Steps",
        ]
    )
    next_steps = payload.get("recommended_next_steps", []) or []
    if next_steps:
        lines.extend(f"- {step}" for step in next_steps)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
        "LLM Audit",
        f"- Provider: {payload.get('llm_audit', {}).get('provider', 'N/A')}",
            f"- Model: {payload.get('llm_audit', {}).get('model', 'N/A')}",
            f"- Prompt Tokens: {payload.get('llm_audit', {}).get('prompt_tokens', 0)}",
            f"- Response Tokens: {payload.get('llm_audit', {}).get('response_tokens', 0)}",
            f"- Total Tokens: {payload.get('llm_audit', {}).get('total_tokens', 0)}",
            f"- Estimated Cost USD: {payload.get('llm_audit', {}).get('estimated_cost_usd', '0')}",
        ]
    )
    if payload.get("strategist_note"):
        lines.extend(["", "Strategist Note", payload["strategist_note"]])
    return "\n".join(lines)


def _group_competitor_panels(panels: list[Panel]) -> list[dict]:
    grouped: dict[str, list[Panel]] = defaultdict(list)
    for panel in panels:
        grouped[panel.company.name].append(panel)
    return [
        {
            "company": company,
            "panels": sorted(items, key=lambda item: item.name.lower()),
        }
        for company, items in sorted(grouped.items(), key=lambda item: item[0].lower())
    ]


def _filter_coverage_payload(payload: dict, disease_filter: str) -> dict:
    if not disease_filter:
        return payload

    filtered_results = [
        item for item in payload["results"]
        if item["guideline"].cancer_type.lower() == disease_filter.lower()
    ]
    matched_total = sum(item["matched_count"] for item in filtered_results)
    reference_total = sum(item["reference_count"] for item in filtered_results)
    average = (matched_total * 100 / reference_total) if reference_total else 0
    covered_guidelines = [item for item in filtered_results if item["matched_count"] > 0]
    gap_guidelines = [
        item for item in sorted(
            filtered_results,
            key=lambda item: (item["coverage_percent"], item["guideline"].cancer_type.lower(), item["guideline"].name.lower()),
        )
        if item["missing_count"] > 0
    ]
    return {
        **payload,
        "results": filtered_results,
        "guideline_count": len(filtered_results),
        "average_coverage": f"{average:.2f}",
        "covered_guidelines": covered_guidelines,
        "gap_guidelines": gap_guidelines,
        "top_guidelines": filtered_results[:6],
        "lowest_guidelines": gap_guidelines[:6],
    }


def _attach_source_pages(items, page_lookup: dict[int, int]) -> None:
    for item in items:
        source_section = getattr(item, "source_section", None)
        item.source_page_number = page_lookup.get(source_section.pk) if source_section else None


def home(request):
    context = {
        "page_title": "MedStratix",
        "hero_eyebrow": "Healthcare Marketing",
        "hero_title": "Growth strategy for healthcare brands that need clarity, trust, and momentum.",
        "hero_text": (
            "MedStratix helps healthcare teams build credible digital campaigns, stronger "
            "patient engagement, and measurable marketing systems."
        ),
        "hero_points": [
            "Positioning and messaging for healthcare audiences",
            "Campaign planning built around compliance and trust",
            "Landing pages, content, and analytics that support growth",
        ],
        "stats": [
            {"value": "360°", "label": "Integrated campaign planning"},
            {"value": "24/7", "label": "Always-on digital presence"},
            {"value": "1 Hub", "label": "One place for your brand story"},
        ],
        "services": [
            {
                "title": "Guideline Intelligence",
                "text": "Upload oncology guidelines and turn them into a structured molecular intelligence layer.",
            },
            {
                "title": "Panel Comparison",
                "text": "Evaluate panel coverage against actionable biomarkers and therapy-linked gaps.",
            },
            {
                "title": "Strategy Outputs",
                "text": "Translate biomarker and treatment relevance into positioning and commercial insights.",
            },
        ],
    }
    return render(request, "medstratix/home.html", context)


class SignInView(LoginView):
    template_name = "registration/login.html"
    authentication_form = SignInForm
    redirect_authenticated_user = True


class SignOutView(LogoutView):
    next_page = reverse_lazy("medstratix:home")


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("medstratix:guideline_workspace")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Your account is ready. You can start uploading guidelines now.")
        return response


@login_required
def guideline_workspace(request):
    if request.method == "POST":
        form = GuidelineUploadForm(request.POST, request.FILES)
        if form.is_valid():
            guideline = form.save()
            try:
                result = process_guideline_document(guideline)
                messages.success(
                    request,
                    f"{guideline.name} processed successfully. "
                    f"Profile: {result['parser_family']} / {result['molecular_style']}. "
                    f"Created {result['sections_created']} sections, "
                    f"{result['biomarker_definitions_created']} biomarker definitions, and "
                    f"{result['therapy_rules_created']} therapy rules.",
                )
            except Exception as exc:
                messages.error(
                    request,
                    f"{guideline.name} was uploaded, but processing failed: {exc}",
                )
            return redirect("medstratix:guideline_workspace")
    else:
        form = GuidelineUploadForm()

    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    sort_by = request.GET.get("sort", "updated")

    guideline_qs = GuidelineDocument.objects.all()
    if search_query:
        guideline_qs = guideline_qs.filter(
            Q(name__icontains=search_query)
            | Q(cancer_type__icontains=search_query)
            | Q(version__icontains=search_query)
        )
    if status_filter:
        guideline_qs = guideline_qs.filter(status=status_filter)

    workspace_sort_map = {
        "updated": ("-updated_at", "-created_at"),
        "name": ("name",),
        "cancer": ("cancer_type", "name"),
        "biomarkers": ("-created_at",),
    }
    guideline_qs = guideline_qs.order_by(*workspace_sort_map.get(sort_by, workspace_sort_map["updated"]))
    paginator = Paginator(guideline_qs, 8)
    page_obj = paginator.get_page(request.GET.get("page"))
    paged_guidelines = list(page_obj.object_list)
    reviewed_count = guideline_qs.filter(status="reviewed").count()
    extracted_count = guideline_qs.filter(status="extracted").count()
    imported_count = guideline_qs.filter(status="imported").count()
    total_biomarkers = 0
    total_therapies = 0
    total_testing = 0
    deep_count = 0
    starter_count = 0
    light_count = 0
    guideline_snapshots = []
    for guideline in paged_guidelines:
        snapshot = _guideline_snapshot(guideline)
        guideline_snapshots.append(snapshot)
        total_biomarkers += snapshot["biomarkers"]
        total_therapies += snapshot["therapies"]
        total_testing += snapshot["testing"]
        if snapshot["depth_label"] == "Deep":
            deep_count += 1
        elif snapshot["depth_label"] == "Starter":
            starter_count += 1
        else:
            light_count += 1

    context = {
        "page_title": "Guideline Workspace",
        "form": form,
        "guidelines": guideline_snapshots,
        "page_obj": page_obj,
        "library_summary": {
            "total": guideline_qs.count(),
            "reviewed": reviewed_count,
            "extracted": extracted_count,
            "imported": imported_count,
            "page_biomarkers": total_biomarkers,
            "page_therapies": total_therapies,
            "page_testing": total_testing,
            "recent_deep": deep_count,
            "recent_starter": starter_count,
            "recent_light": light_count,
        },
        "filters": {
            "q": search_query,
            "status": status_filter,
            "sort": sort_by,
            "query_suffix": _query_without_page(request),
        },
        "active_filter_chips": _active_filter_chips(
            {"q": search_query, "status": status_filter, "sort": sort_by},
            reverse_lazy("medstratix:guideline_workspace"),
        ),
    }
    return render(request, "medstratix/guideline_workspace.html", context)


@login_required
def panel_workspace(request):
    if request.method == "POST":
        upload_kind = request.POST.get("upload_kind", "").strip()
        company_type = CompanyType.YOURS if upload_kind == "yours" else CompanyType.COMPETITOR
        your_form = PanelUploadForm(
            request.POST if upload_kind == "yours" else None,
            request.FILES if upload_kind == "yours" else None,
            prefix="yours",
            company_type=CompanyType.YOURS,
        )
        competitor_form = PanelUploadForm(
            request.POST if upload_kind == "competitor" else None,
            request.FILES if upload_kind == "competitor" else None,
            prefix="competitor",
            company_type=CompanyType.COMPETITOR,
        )
        active_form = your_form if upload_kind == "yours" else competitor_form
        if active_form.is_valid():
            result = save_uploaded_panel(
                company_name=active_form.cleaned_data["company_name"],
                company_type=company_type,
                panel_name=active_form.cleaned_data["panel_name"],
                website_url=active_form.cleaned_data.get("website_url", ""),
                gene_panel_available=active_form.cleaned_data.get("gene_panel_available", False),
                sample_type=active_form.cleaned_data.get("sample_type", SampleType.TISSUE),
                supports_dna_ngs=active_form.cleaned_data.get("supports_dna_ngs", False),
                supports_rna_ngs=active_form.cleaned_data.get("supports_rna_ngs", False),
                supports_fusions=active_form.cleaned_data.get("supports_fusions", False),
                supports_cnv=active_form.cleaned_data.get("supports_cnv", False),
                supports_msi=active_form.cleaned_data.get("supports_msi", False),
                supports_tmb=active_form.cleaned_data.get("supports_tmb", False),
                supports_ihc=active_form.cleaned_data.get("supports_ihc", False),
                supports_fish=active_form.cleaned_data.get("supports_fish", False),
                price=active_form.cleaned_data.get("price"),
                price_currency=active_form.cleaned_data.get("price_currency", "BDT"),
                tat=active_form.cleaned_data.get("tat", ""),
                gene_text=active_form.cleaned_data.get("gene_text", ""),
                gene_file=active_form.cleaned_data.get("gene_file"),
            )
            messages.success(
                request,
                f"{result['panel'].name} saved for {result['company'].name}. "
                f"{'Loaded ' + str(result['gene_count']) + ' genes.' if result['gene_panel_available'] else 'Gene panel data marked unavailable.'} {result['price_note']}",
            )
            return redirect("medstratix:panel_workspace")
    else:
        your_form = PanelUploadForm(prefix="yours", company_type=CompanyType.YOURS)
        competitor_form = PanelUploadForm(prefix="competitor", company_type=CompanyType.COMPETITOR)

    search_query = request.GET.get("q", "").strip()
    owner_filter = request.GET.get("owner", "").strip()
    sort_by = request.GET.get("sort", "updated")

    panel_qs = Panel.objects.select_related("company").prefetch_related("panel_genes__gene")
    if search_query:
        panel_qs = panel_qs.filter(
            Q(name__icontains=search_query)
            | Q(company__name__icontains=search_query)
            | Q(panel_genes__gene__symbol__icontains=search_query)
        ).distinct()
    if owner_filter == "yours":
        panel_qs = panel_qs.filter(company__type=CompanyType.YOURS)
    elif owner_filter == "competitor":
        panel_qs = panel_qs.filter(company__type=CompanyType.COMPETITOR)

    panel_sort_map = {
        "updated": ("-updated_at", "-created_at"),
        "name": ("name",),
        "company": ("company__name", "name"),
        "price": ("price", "name"),
    }
    panel_qs = panel_qs.order_by(*panel_sort_map.get(sort_by, panel_sort_map["updated"]))
    paginator = Paginator(panel_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    panel_snapshots = [_panel_snapshot(panel) for panel in page_obj.object_list]

    your_count = panel_qs.filter(company__type=CompanyType.YOURS).count()
    competitor_count = panel_qs.filter(company__type=CompanyType.COMPETITOR).count()

    context = {
        "page_title": "Panel Workspace",
        "your_form": your_form,
        "competitor_form": competitor_form,
        "panels": panel_snapshots,
        "page_obj": page_obj,
        "summary": {
            "total": panel_qs.count(),
            "your_count": your_count,
            "competitor_count": competitor_count,
        },
        "filters": {
            "q": search_query,
            "owner": owner_filter,
            "sort": sort_by,
            "query_suffix": _query_without_page(request),
        },
        "active_filter_chips": _active_filter_chips(
            {"q": search_query, "owner": owner_filter, "sort": sort_by},
            reverse_lazy("medstratix:panel_workspace"),
        ),
    }
    return render(request, "medstratix/panel_workspace.html", context)


@login_required
def panel_edit(request, pk):
    panel = get_object_or_404(Panel.objects.select_related("company"), pk=pk)
    if request.method == "POST":
        form = PanelUploadForm(request.POST, request.FILES, company_type=panel.company.type)
        if form.is_valid():
            result = save_uploaded_panel(
                company_name=form.cleaned_data["company_name"],
                company_type=panel.company.type,
                panel_name=form.cleaned_data["panel_name"],
                website_url=form.cleaned_data.get("website_url", ""),
                gene_panel_available=form.cleaned_data.get("gene_panel_available", False),
                sample_type=form.cleaned_data.get("sample_type", SampleType.TISSUE),
                supports_dna_ngs=form.cleaned_data.get("supports_dna_ngs", False),
                supports_rna_ngs=form.cleaned_data.get("supports_rna_ngs", False),
                supports_fusions=form.cleaned_data.get("supports_fusions", False),
                supports_cnv=form.cleaned_data.get("supports_cnv", False),
                supports_msi=form.cleaned_data.get("supports_msi", False),
                supports_tmb=form.cleaned_data.get("supports_tmb", False),
                supports_ihc=form.cleaned_data.get("supports_ihc", False),
                supports_fish=form.cleaned_data.get("supports_fish", False),
                price=form.cleaned_data.get("price"),
                price_currency=form.cleaned_data.get("price_currency", "BDT"),
                tat=form.cleaned_data.get("tat", ""),
                gene_text=form.cleaned_data.get("gene_text", ""),
                gene_file=form.cleaned_data.get("gene_file"),
                existing_panel=panel,
            )
            messages.success(
                request,
                f"{result['panel'].name} updated successfully. "
                f"{'Loaded ' + str(result['gene_count']) + ' genes.' if result['gene_panel_available'] else 'Gene panel data marked unavailable.'} "
                f"{result['price_note']}"
            )
            return redirect("medstratix:panel_workspace")
    else:
        form = PanelUploadForm(initial=_panel_initial(panel), company_type=panel.company.type)

    context = {
        "page_title": f"Edit {panel.name}",
        "panel": panel,
        "form": form,
    }
    return render(request, "medstratix/panel_edit.html", context)


@login_required
def panel_compare_setup(request):
    if request.method == "POST":
        form = PanelComparisonSelectForm(request.POST)
        if form.is_valid():
            selected_your_panels = list(form.cleaned_data["your_panels"])
            selected_competitors = list(form.cleaned_data["competitor_panels"])
            if not selected_your_panels or not selected_competitors:
                messages.error(request, "Choose at least one of your panels and at least one competitor panel for comparison.")
            else:
                comparison_run = ComparisonRun.objects.create(
                    created_by=request.user,
                    name=f"Comparison run for {len(selected_your_panels)} your panels vs {len(selected_competitors)} competitor panels",
                    summary_json={
                        "your_panels": [panel.pk for panel in selected_your_panels],
                        "competitor_panels": [panel.pk for panel in selected_competitors],
                    },
                )
                comparison_run.your_panels.set(selected_your_panels)
                comparison_run.competitor_panels.set(selected_competitors)
                return redirect(
                    f"{reverse_lazy('medstratix:panel_compare_result')}"
                    f"?run={comparison_run.pk}&your_panels={_serialize_panel_ids(selected_your_panels)}&competitors={_serialize_competitor_ids(selected_competitors)}"
                )
    else:
        form = PanelComparisonSelectForm()

    context = {
        "page_title": "Panel Comparison Setup",
        "form": form,
    }
    return render(request, "medstratix/panel_compare_setup.html", context)


@login_required
def panel_compare_result(request):
    run_id = request.GET.get("run", "").strip()
    comparison_run = None
    if run_id.isdigit():
        comparison_run = ComparisonRun.objects.prefetch_related("your_panels__company", "competitor_panels__company").filter(pk=int(run_id)).first()

    your_panel_ids = _parse_panel_ids(request.GET.get("your_panels", ""))
    competitor_ids = _parse_competitor_ids(request.GET.get("competitors", ""))
    disease_filter = request.GET.get("disease", "").strip()

    if not comparison_run and (not your_panel_ids or not competitor_ids):
        messages.error(request, "Select at least one of your panels and at least one competitor panel to view results.")
        return redirect("medstratix:panel_compare_setup")

    if comparison_run:
        your_panels = list(comparison_run.your_panels.all().order_by("company__name", "name"))
        competitor_panels = list(comparison_run.competitor_panels.all().order_by("company__name", "name"))
    else:
        your_panels = list(
            Panel.objects.select_related("company")
            .filter(pk__in=your_panel_ids, company__type=CompanyType.YOURS)
            .order_by("company__name", "name")
        )
        competitor_panels = list(
            Panel.objects.select_related("company")
            .filter(pk__in=competitor_ids, company__type=CompanyType.COMPETITOR)
            .order_by("company__name", "name")
        )
    if not your_panels or not competitor_panels:
        messages.error(request, "No competitor panels were found for this comparison.")
        return redirect("medstratix:panel_compare_setup")

    primary_your_panel = your_panels[0]
    your_panel_ids = [panel.pk for panel in your_panels]
    competitor_ids = [panel.pk for panel in competitor_panels]
    comparison_bundle = build_comparison_bundle(your_panels, competitor_panels)
    market_accounts = list(MarketAccount.objects.prefetch_related("stakeholders").order_by("name"))
    strategy_model_options = list_strategy_models()
    default_strategy_model = next(
        (item["code"] for item in strategy_model_options if item.get("recommended")),
        strategy_model_options[0]["code"] if strategy_model_options else "gemini-2.5-pro",
    )
    disease_choices = sorted(
        {item["guideline"].cancer_type for item in comparison_bundle["your_guideline_coverage"]["results"] if item["guideline"].cancer_type}
    )
    grouped_competitors = _group_competitor_panels(competitor_panels)

    if disease_filter:
        comparison_bundle = {
            **comparison_bundle,
            "your_guideline_coverage": _filter_coverage_payload(comparison_bundle["your_guideline_coverage"], disease_filter),
            "competitor_guideline_coverages": [
                _filter_coverage_payload(payload, disease_filter)
                for payload in comparison_bundle["competitor_guideline_coverages"]
            ],
        }

    strategy_outputs = []
    selected_market_account_ids = []
    strategist_note = ""
    selected_strategy_model = default_strategy_model
    if request.method == "POST":
        competitor_panel_id = request.POST.get("competitor_panel_id", "").strip()
        strategy_scope = request.POST.get("strategy_scope", "single").strip() or "single"
        selected_market_account_ids = request.POST.getlist("market_account_ids")
        strategist_note = request.POST.get("strategist_note", "").strip()
        requested_strategy_model = request.POST.get("strategy_model", "").strip()
        valid_model_codes = {item["code"] for item in strategy_model_options}
        selected_strategy_model = requested_strategy_model if requested_strategy_model in valid_model_codes else default_strategy_model
        target_competitor = next((panel for panel in competitor_panels if str(panel.pk) == competitor_panel_id), None)
        selected_accounts = _selected_market_accounts(market_accounts, selected_market_account_ids)
        primary_account = selected_accounts[0] if selected_accounts else None
        selected_stakeholders = []
        for account in selected_accounts:
            selected_stakeholders.extend(list(account.stakeholders.all()))
        if strategy_scope == "set" or target_competitor:
            competitor_profile = build_panel_set_profile(competitor_panels) if strategy_scope == "set" else build_panel_set_profile([target_competitor])
            competitor_label = competitor_profile["name"] if strategy_scope == "set" else target_competitor.name
            logger.info(
                "Strategy generation requested your_panel=%s competitor_panel=%s disease_filter=%s market_accounts=%s",
                comparison_bundle["your_panel_set"]["name"],
                competitor_label,
                disease_filter or "ALL",
                [account.name for account in selected_accounts],
            )
            competitor_bundle = (
                build_guideline_coverage(competitor_profile)
                if strategy_scope == "set"
                else next(
                    (payload for payload in comparison_bundle["competitor_guideline_coverages"] if payload["panel"].pk == target_competitor.pk),
                    None,
                )
            )
            comparison_pair = (
                compare_panel_profiles(comparison_bundle["your_panel_set"], competitor_profile)
                if strategy_scope == "set"
                else next(
                    (payload for payload in comparison_bundle["competitor_comparisons"] if payload["competitor_panel"].pk == target_competitor.pk),
                    None,
                )
            )
            try:
                strategy_result = generate_structured_strategy(
                    your_panel=comparison_bundle["your_panel_set"],
                    competitor_panel=competitor_profile,
                    comparison_pair=comparison_pair,
                    your_guideline_coverage=comparison_bundle["your_guideline_coverage"],
                    competitor_guideline_coverage=competitor_bundle,
                    disease_filter=disease_filter,
                    market_accounts=selected_accounts,
                    stakeholders=selected_stakeholders,
                    strategist_note=strategist_note,
                    model_name_override=selected_strategy_model,
                )
                strategy_payload = strategy_result["response_json"]
                strategy_record = StrategyReport.objects.create(
                    your_panel=primary_your_panel,
                    competitor_panel=competitor_panels[0],
                    market_account=primary_account,
                    title=strategy_payload.get("title", "").strip(),
                    disease_focus=disease_filter,
                    status="completed",
                    executive_summary=strategy_payload.get("executive_summary", ""),
                    swot_json=strategy_payload.get("swot", {}),
                    market_gap_json=strategy_payload.get("market_gap", {}),
                    guideline_advantages_json=strategy_payload.get("guideline_coverage_and_advantages", {}),
                    campaigns_json=strategy_payload.get("marketing_campaigns", []),
                    sales_pitch_text=strategy_payload.get("sales_pitch", ""),
                    llm_provider=strategy_result["provider"],
                    llm_model=strategy_result["model"],
                    report_json={
                        "disease_filter": disease_filter,
                        "market_account": primary_account.name if primary_account else "",
                        "market_accounts": [
                            {
                                "id": account.pk,
                                "name": account.name,
                                "city": account.city,
                                "institution_type": account.get_institution_type_display(),
                            }
                            for account in selected_accounts
                        ],
                        "recommended_next_steps": strategy_payload.get("recommended_next_steps", []),
                        "raw_strategy_payload": strategy_payload,
                        "compare_query": {
                            "run": comparison_run.pk if comparison_run else None,
                            "your_panels": your_panel_ids,
                            "competitors": competitor_ids,
                        },
                        "your_panels": [
                            {
                                "id": panel.pk,
                                "name": panel.name,
                                "company": panel.company.name,
                                "sample_type": panel.get_sample_type_display(),
                            }
                            for panel in your_panels
                        ],
                        "competitor_panels": [
                            {
                                "id": panel.pk,
                                "name": panel.name,
                                "company": panel.company.name,
                                "sample_type": panel.get_sample_type_display(),
                            }
                            for panel in competitor_panels
                        ],
                        "strategist_note": strategist_note,
                        "requested_strategy_model": selected_strategy_model,
                        "strategy_scope": strategy_scope,
                    },
                )
                LLMGenerationLog.objects.create(
                    strategy_report=strategy_record,
                    provider=strategy_result["provider"],
                    model_name=strategy_result["model"],
                    prompt_text=strategy_result["prompt_text"],
                    response_text=strategy_result["response_text"],
                    response_json=strategy_payload,
                    prompt_tokens=strategy_result["prompt_tokens"],
                    response_tokens=strategy_result["response_tokens"],
                    total_tokens=strategy_result["total_tokens"],
                    estimated_cost_usd=strategy_result["estimated_cost_usd"],
                    status="completed",
                )
                logger.info(
                    "Strategy report saved report_id=%s your_panel=%s competitor_panel=%s",
                    strategy_record.pk,
                    comparison_bundle["your_panel_set"]["name"],
                    competitor_label,
                )
                messages.success(request, f"Strategy draft generated for {competitor_label}.")
                strategy_outputs.append(
                    {
                        "competitor_panel": target_competitor or competitor_panels[0],
                        "competitor_label": competitor_label,
                        "strategy_text": strategy_payload.get("executive_summary", ""),
                        "report_id": strategy_record.pk,
                        "title": strategy_record.title,
                    }
                )
            except Exception as exc:
                logger.exception(
                    "Strategy generation failed your_panel=%s competitor_panel=%s disease_filter=%s",
                    comparison_bundle["your_panel_set"]["name"],
                    competitor_label,
                    disease_filter or "ALL",
                )
                messages.error(request, f"Strategy generation failed for {competitor_label}: {exc}")

    existing_strategy_reports = list(
        StrategyReport.objects.filter(
            your_panel__in=your_panels,
            competitor_panel__in=competitor_panels,
        )
        .select_related("competitor_panel")
        .order_by("-created_at")[:8]
    )

    context = {
        "page_title": "Panel Comparison Results",
        "comparison_run": comparison_run,
        "your_panels": your_panels,
        "competitor_panels": competitor_panels,
        "grouped_competitors": grouped_competitors,
        "comparison_bundle": comparison_bundle,
        "market_accounts": market_accounts,
        "filters": {
            "disease": disease_filter,
            "run": comparison_run.pk if comparison_run else "",
            "your_panels": _serialize_panel_ids(your_panels),
            "competitors": _serialize_competitor_ids(competitor_panels),
        },
        "disease_choices": disease_choices,
        "strategy_outputs": strategy_outputs,
        "existing_strategy_reports": existing_strategy_reports,
        "selected_market_account_ids": selected_market_account_ids,
        "strategist_note": strategist_note,
        "strategy_model_options": strategy_model_options,
        "selected_strategy_model": selected_strategy_model,
    }
    return render(request, "medstratix/panel_compare_result.html", context)


@login_required
def strategy_workspace(request):
    search_query = request.GET.get("q", "").strip()
    disease_filter = request.GET.get("disease", "").strip()

    reports = StrategyReport.objects.select_related("your_panel", "competitor_panel").prefetch_related("llm_logs")
    if search_query:
        reports = reports.filter(
            Q(title__icontains=search_query)
            | Q(your_panel__name__icontains=search_query)
            | Q(competitor_panel__name__icontains=search_query)
            | Q(disease_focus__icontains=search_query)
        )
    if disease_filter:
        reports = reports.filter(disease_focus__icontains=disease_filter)

    reports = reports.order_by("-created_at")
    paginator = Paginator(reports, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_title": "Strategy Workspace",
        "reports": list(page_obj.object_list),
        "page_obj": page_obj,
        "filters": {
            "q": search_query,
            "disease": disease_filter,
            "query_suffix": _query_without_page(request),
        },
        "active_filter_chips": _active_filter_chips(
            {"q": search_query, "disease": disease_filter},
            reverse_lazy("medstratix:strategy_workspace"),
        ),
    }
    return render(request, "medstratix/strategy_workspace.html", context)


@login_required
def comparison_run_workspace(request):
    runs = ComparisonRun.objects.prefetch_related("your_panels__company", "competitor_panels__company", "marketing_plans").select_related("created_by")
    paginator = Paginator(runs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "page_title": "Comparison Runs",
        "runs": list(page_obj.object_list),
        "page_obj": page_obj,
    }
    return render(request, "medstratix/comparison_run_workspace.html", context)


@login_required
def comparison_run_detail(request, pk):
    run = get_object_or_404(
        ComparisonRun.objects.prefetch_related("your_panels__company", "competitor_panels__company", "marketing_plans"),
        pk=pk,
    )
    context = {
        "page_title": run.name or f"Comparison Run {run.pk}",
        "run": run,
    }
    return render(request, "medstratix/comparison_run_detail.html", context)


@login_required
def comparison_run_export(request, pk, fmt):
    run = get_object_or_404(
        ComparisonRun.objects.select_related("created_by").prefetch_related("your_panels__company", "competitor_panels__company", "marketing_plans"),
        pk=pk,
    )
    export_format = (fmt or "").lower().strip()
    filename = _comparison_run_export_filename(run, export_format)

    if export_format == "docx":
        document_buffer = build_comparison_run_docx(run)
        response = HttpResponse(
            document_buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    if export_format == "json":
        payload = {
            "id": run.pk,
            "name": run.name,
            "created_by": getattr(run.created_by, "username", ""),
            "disease_filter": run.disease_filter,
            "your_panels": [
                {
                    "id": panel.pk,
                    "company": panel.company.name,
                    "name": panel.name,
                    "sample_type": panel.get_sample_type_display(),
                    "price_bdt": str(panel.price) if panel.price is not None else "",
                    "tat": panel.tat,
                }
                for panel in run.your_panels.all()
            ],
            "competitor_panels": [
                {
                    "id": panel.pk,
                    "company": panel.company.name,
                    "name": panel.name,
                    "sample_type": panel.get_sample_type_display(),
                    "price_bdt": str(panel.price) if panel.price is not None else "",
                    "tat": panel.tat,
                }
                for panel in run.competitor_panels.all()
            ],
            "summary_json": run.summary_json,
            "linked_marketing_plans": [
                {
                    "id": plan.pk,
                    "title": plan.title,
                    "output_style": plan.output_style,
                }
                for plan in run.marketing_plans.all()
            ],
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat(),
        }
        response = JsonResponse(payload, json_dumps_params={"indent": 2})
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    messages.error(request, "Unsupported comparison-run export format.")
    return redirect("medstratix:comparison_run_detail", pk=run.pk)


@login_required
def marketing_plan_builder(request):
    strategy_model_options = list_strategy_models()
    model_choices = [(item["code"], f"{item['label']}{' (Recommended)' if item.get('recommended') else ''}") for item in strategy_model_options]

    preselected_source_plans = []
    source_ids = _parse_panel_ids(request.GET.get("source_plans", ""))
    if source_ids:
        source_plans_map = MarketingPlan.objects.in_bulk(source_ids)
        preselected_source_plans = [source_plans_map[source_id] for source_id in source_ids if source_id in source_plans_map]

    if request.method == "POST":
        form = MarketingPlanBuilderForm(request.POST, model_choices=model_choices)
        if form.is_valid():
            request_started_at = time.perf_counter()
            logger.info(
                "Marketing plan builder accepted title=%s output_style=%s include_product_context=%s",
                form.cleaned_data["title"],
                form.cleaned_data["output_style"],
                form.cleaned_data["include_product_context"],
            )
            source_plans = list(form.cleaned_data["source_plans"])
            market_accounts = list(form.cleaned_data["market_accounts"])
            your_panels = list(form.cleaned_data["your_panels"])
            competitor_panels = list(form.cleaned_data["competitor_panels"])
            include_product_context = form.cleaned_data["include_product_context"]
            sales_expectation = {
                "planning_horizon": form.cleaned_data.get("planning_horizon") or "",
                "expected_monthly_samples": form.cleaned_data.get("expected_monthly_samples") or "",
                "expected_quarterly_revenue_bdt": str(form.cleaned_data.get("expected_quarterly_revenue_bdt") or ""),
                "expected_year_one_revenue_bdt": str(form.cleaned_data.get("expected_year_one_revenue_bdt") or ""),
                "revenue_guardrail_note": form.cleaned_data.get("revenue_guardrail_note") or "",
            }

            your_summary = _panel_set_summary(your_panels) if include_product_context else {}
            competitor_summary = _panel_set_summary(competitor_panels) if include_product_context else {}
            comparison_summary = {}
            comparison_run = None

            if include_product_context and your_panels and competitor_panels:
                your_profile = build_panel_set_profile(your_panels)
                competitor_profile = build_panel_set_profile(competitor_panels)
                comparison_summary = _json_safe_value(compare_panel_profiles(your_profile, competitor_profile))
                comparison_run = ComparisonRun.objects.create(
                    created_by=request.user,
                    name=f"Marketing plan run for {form.cleaned_data['title']}",
                    summary_json={
                        "source": "marketing_plan_builder",
                        "your_panels": [panel.pk for panel in your_panels],
                        "competitor_panels": [panel.pk for panel in competitor_panels],
                    },
                )
                comparison_run.your_panels.set(your_panels)
                comparison_run.competitor_panels.set(competitor_panels)

            market_accounts_summary = [
                {
                    "name": account.name,
                    "city": account.city,
                    "institution_type": account.get_institution_type_display(),
                    "decision_style": account.get_decision_style_display(),
                    "disease_focus": account.disease_focus,
                    "price_sensitivity": account.get_price_sensitivity_display(),
                    "tat_sensitivity": account.get_tat_sensitivity_display(),
                    "market_corruption_pressure": account.get_market_corruption_pressure_display(),
                    "referral_distortion_risk": account.get_referral_distortion_risk_display(),
                }
                for account in market_accounts
            ]
            stakeholder_contexts = []
            for account in market_accounts:
                for stakeholder in account.stakeholders.order_by("name"):
                    stakeholder_contexts.append(
                        {
                            "account": account.name,
                            "name": stakeholder.name if stakeholder.is_verified else "",
                            "is_verified": stakeholder.is_verified,
                            "role": stakeholder.get_role_display(),
                            "specialty": stakeholder.specialty,
                            "influence_level": stakeholder.get_influence_level_display(),
                            "evidence_preference": stakeholder.get_evidence_preference_display(),
                            "conference_interest": stakeholder.conference_interest,
                            "service_expectation": stakeholder.service_expectation,
                            "behavioral_notes": stakeholder.behavioral_notes,
                        }
                    )

            source_plan_contexts = [_marketing_plan_context_snapshot(plan) for plan in source_plans]

            save_started_at = time.perf_counter()
            plan = MarketingPlan.objects.create(
                created_by=request.user,
                title=form.cleaned_data["title"],
                objective=form.cleaned_data["objective"],
                geography=form.cleaned_data["geography"],
                disease_focus=form.cleaned_data["disease_focus"],
                output_style=form.cleaned_data["output_style"],
                include_product_context=include_product_context,
                strategist_note=form.cleaned_data["strategist_note"],
                market_account=market_accounts[0] if market_accounts else None,
                comparison_run=comparison_run,
                status="queued",
                executive_summary="",
                llm_provider="google_genai",
                llm_model=form.cleaned_data["strategy_model"],
                plan_json={},
                plan_text="",
                report_json={
                    "source_plans": [
                        {
                            "id": source_plan.pk,
                            "title": source_plan.title,
                            "output_style": source_plan.output_style,
                            "output_style_label": MARKETING_PLAN_STYLE_LABELS.get(source_plan.output_style, source_plan.output_style),
                        }
                        for source_plan in source_plans
                    ],
                    "market_accounts": market_accounts_summary,
                    "stakeholder_contexts": stakeholder_contexts,
                    "your_panels": [
                        {"id": panel.pk, "name": panel.name, "company": panel.company.name, "sample_type": panel.get_sample_type_display()}
                        for panel in your_panels
                    ],
                    "competitor_panels": [
                        {"id": panel.pk, "name": panel.name, "company": panel.company.name, "sample_type": panel.get_sample_type_display()}
                        for panel in competitor_panels
                    ],
                    "strategist_note": form.cleaned_data["strategist_note"],
                    "sales_expectation": sales_expectation,
                    "source_plan_contexts": source_plan_contexts,
                    "plan_title_source": "user_input",
                    "generation_request": {
                        "title": form.cleaned_data["title"],
                        "objective": form.cleaned_data["objective"],
                        "geography": form.cleaned_data["geography"],
                        "disease_focus": form.cleaned_data["disease_focus"],
                        "output_style": form.cleaned_data["output_style"],
                        "include_product_context": include_product_context,
                        "sales_expectation": sales_expectation,
                        "strategist_note": form.cleaned_data["strategist_note"],
                        "market_accounts_summary": market_accounts_summary,
                        "stakeholder_contexts": stakeholder_contexts,
                        "your_panel_summary": your_summary,
                        "competitor_panel_summary": competitor_summary,
                        "comparison_summary": comparison_summary,
                        "source_plan_contexts": source_plan_contexts,
                        "strategy_model": form.cleaned_data["strategy_model"],
                    },
                },
            )
            logger.info(
                "Marketing plan saved plan_id=%s title=%s elapsed_ms=%s",
                plan.pk,
                plan.title,
                int((time.perf_counter() - save_started_at) * 1000),
            )
            enqueue_started_at = time.perf_counter()
            try:
                async_result = generate_marketing_plan_task.delay(plan.pk)
            except Exception as exc:
                logger.exception("Failed to enqueue marketing plan task plan_id=%s", plan.pk)
                report_json = dict(plan.report_json or {})
                report_json["generation_error"] = str(exc)
                plan.status = "failed"
                plan.report_json = report_json
                plan.save(update_fields=["status", "report_json", "updated_at"])
                form.add_error(None, f"Marketing plan queueing failed: {exc}")
                context = {
                    "page_title": "Marketing Plan Builder",
                    "form": form,
                    "strategy_model_options": strategy_model_options,
                    "preselected_source_plans": source_plans,
                }
                return render(request, "medstratix/marketing_plan_builder.html", context, status=200)
            report_json = dict(plan.report_json or {})
            report_json["async_task"] = {
                "id": async_result.id,
                "state": "PENDING",
            }
            plan.report_json = report_json
            plan.save(update_fields=["report_json", "updated_at"])
            logger.info(
                "Marketing plan task queued plan_id=%s task_id=%s enqueue_elapsed_ms=%s total_elapsed_ms=%s",
                plan.pk,
                async_result.id,
                int((time.perf_counter() - enqueue_started_at) * 1000),
                int((time.perf_counter() - request_started_at) * 1000),
            )
            messages.success(request, "Marketing plan queued successfully. We are generating it in the background.")
            logger.info("Redirecting to marketing plan detail plan_id=%s", plan.pk)
            return redirect("medstratix:marketing_plan_detail", pk=plan.pk)
    else:
        initial = {}
        if preselected_source_plans:
            primary_source = preselected_source_plans[0]
            initial = {
                "source_plans": [plan.pk for plan in preselected_source_plans],
                "title": f"{primary_source.title} - {MARKETING_PLAN_STYLE_LABELS.get(request.GET.get('output_style', ''), 'Next Plan')}",
                "objective": primary_source.objective,
                "geography": primary_source.geography,
                "disease_focus": primary_source.disease_focus,
                "planning_horizon": primary_source.report_json.get("sales_expectation", {}).get("planning_horizon", ""),
                "expected_monthly_samples": primary_source.report_json.get("sales_expectation", {}).get("expected_monthly_samples", ""),
                "expected_quarterly_revenue_bdt": primary_source.report_json.get("sales_expectation", {}).get("expected_quarterly_revenue_bdt", ""),
                "expected_year_one_revenue_bdt": primary_source.report_json.get("sales_expectation", {}).get("expected_year_one_revenue_bdt", ""),
                "revenue_guardrail_note": primary_source.report_json.get("sales_expectation", {}).get("revenue_guardrail_note", ""),
                "strategist_note": primary_source.strategist_note,
                "include_product_context": primary_source.include_product_context,
            }
        requested_output_style = request.GET.get("output_style", "").strip()
        if requested_output_style in MARKETING_PLAN_STYLE_LABELS:
            initial["output_style"] = requested_output_style
        form = MarketingPlanBuilderForm(initial=initial, model_choices=model_choices)

    context = {
        "page_title": "Marketing Plan Builder",
        "form": form,
        "strategy_model_options": strategy_model_options,
        "preselected_source_plans": preselected_source_plans,
    }
    return render(request, "medstratix/marketing_plan_builder.html", context)


@login_required
def marketing_plan_workspace(request):
    plans = MarketingPlan.objects.select_related("created_by", "market_account", "comparison_run").order_by("-created_at")
    paginator = Paginator(plans, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    plans_for_page = list(page_obj.object_list)
    for plan in plans_for_page:
        plan.display_summary = _marketing_plan_display_summary(plan)
    context = {
        "page_title": "Marketing Plans",
        "plans": plans_for_page,
        "page_obj": page_obj,
    }
    return render(request, "medstratix/marketing_plan_workspace.html", context)


@login_required
def final_marketing_report_builder(request):
    if request.method == "POST":
        form = FinalMarketingReportBuilderForm(request.POST)
        if form.is_valid():
            selected_plans = list(form.cleaned_data["selected_plans"])
            ordered_plans = _ordered_marketing_plans(
                selected_plans,
                form.cleaned_data["chronology_mode"],
                form.cleaned_data.get("custom_plan_order") or [],
            )
            payload = _final_marketing_report_payload(ordered_plans, form.cleaned_data.get("strategist_note", ""))
            report = FinalMarketingReport.objects.create(
                created_by=request.user,
                title=form.cleaned_data["title"],
                chronology_mode=form.cleaned_data["chronology_mode"],
                ordered_plan_ids=[plan.pk for plan in ordered_plans],
                executive_summary=payload.get("combined_summary", ""),
                report_json=payload,
            )
            messages.success(request, "Final marketing report created successfully.")
            return redirect("medstratix:final_marketing_report_detail", pk=report.pk)
    else:
        form = FinalMarketingReportBuilderForm()

    context = {
        "page_title": "Final Report Builder",
        "form": form,
    }
    return render(request, "medstratix/final_marketing_report_builder.html", context)


@login_required
def final_marketing_report_workspace(request):
    reports = FinalMarketingReport.objects.select_related("created_by").order_by("-created_at")
    paginator = Paginator(reports, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "page_title": "Final Marketing Reports",
        "reports": list(page_obj.object_list),
        "page_obj": page_obj,
    }
    return render(request, "medstratix/final_marketing_report_workspace.html", context)


@login_required
def final_marketing_report_detail(request, pk):
    report = get_object_or_404(FinalMarketingReport.objects.select_related("created_by"), pk=pk)
    ordered_plans = []
    plans_by_id = MarketingPlan.objects.in_bulk(report.ordered_plan_ids or [])
    for plan_id in report.ordered_plan_ids or []:
        if plan_id in plans_by_id:
            ordered_plans.append(plans_by_id[plan_id])
    context = {
        "page_title": report.title,
        "report": report,
        "ordered_plans": ordered_plans,
        "ordered_sections": (report.report_json or {}).get("ordered_plans", []),
        "strategist_note": (report.report_json or {}).get("strategist_note", ""),
    }
    return render(request, "medstratix/final_marketing_report_detail.html", context)


@login_required
def final_marketing_report_export(request, pk, fmt):
    report = get_object_or_404(FinalMarketingReport.objects.select_related("created_by"), pk=pk)
    export_format = (fmt or "").lower().strip()
    filename = _final_marketing_report_export_filename(report, export_format)

    if export_format == "json":
        response = JsonResponse(report.report_json or {}, json_dumps_params={"indent": 2})
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    if export_format == "docx":
        document_buffer = build_final_marketing_report_docx(report)
        response = HttpResponse(
            document_buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    if export_format == "pdf":
        pdf_buffer = build_final_marketing_report_pdf(report)
        response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    messages.error(request, "Unsupported export format.")
    return redirect("medstratix:final_marketing_report_detail", pk=report.pk)


@login_required
def marketing_plan_detail(request, pk):
    detail_started_at = time.perf_counter()
    logger.info("Marketing plan detail requested plan_id=%s", pk)
    plan = get_object_or_404(MarketingPlan.objects.select_related("market_account", "comparison_run").prefetch_related("llm_logs"), pk=pk)
    spreadsheet_fields = ["row_type", "label", "period", "formula_logic", "numeric_value", "notes"]
    gantt_fields = ["task", "phase", "owner", "start_period", "end_period", "dependency", "status_signal"]

    if request.method == "POST":
        action = (request.POST.get("plan_action") or "section_overrides").strip()
        if action == "execution_data":
            updated_plan_json = dict(plan.plan_json or {})
            updated_plan_json["spreadsheet_model"] = _collect_execution_rows(request.POST, "spreadsheet", spreadsheet_fields)
            updated_plan_json["gantt_data"] = _collect_execution_rows(request.POST, "gantt", gantt_fields)
            plan.plan_json = updated_plan_json
            plan.save(update_fields=["plan_json", "updated_at"])
            messages.success(request, "Execution rows saved. Future exports and next-step plans will reuse these edited rows.")
            return redirect("medstratix:marketing_plan_detail", pk=plan.pk)
        edit_form = MarketingPlanSectionEditForm(request.POST)
        if edit_form.is_valid():
            report_json = dict(plan.report_json or {})
            report_json["section_overrides"] = {
                key: value.strip()
                for key, value in edit_form.cleaned_data.items()
                if value and value.strip()
            }
            plan.report_json = report_json
            override_summary = report_json["section_overrides"].get("executive_summary_override", "").strip()
            if override_summary:
                plan.executive_summary = override_summary
            plan.save(update_fields=["report_json", "executive_summary", "updated_at"])
            messages.success(request, "Plan edits saved. Future plan generations can reuse these human overrides.")
            return redirect("medstratix:marketing_plan_detail", pk=plan.pk)
    else:
        edit_form = MarketingPlanSectionEditForm(initial=_marketing_plan_edit_initial(plan))

    source_plans = []
    for item in (plan.report_json or {}).get("source_plans", []) or []:
        source_plans.append(item)

    next_plan_links = [
        {"label": "Expand To Detailed Plan", "style": "detailed_plan"},
        {"label": "Turn Into 90-Day Launch Plan", "style": "launch_plan"},
        {"label": "Turn Into Growth Plan", "style": "growth_plan"},
        {"label": "Turn Into Account Plan", "style": "account_plan"},
    ]
    context = {
        "page_title": plan.title,
        "plan": plan,
        "plan_style_label": MARKETING_PLAN_STYLE_LABELS.get(plan.output_style, plan.output_style),
        "plan_summary": plan.report_json.get("section_overrides", {}).get("executive_summary_override")
        or (plan.plan_json or {}).get("narrative_summary")
        or plan.executive_summary,
        "plan_sections": _marketing_plan_display_sections(plan),
        "plan_highlights": _marketing_plan_highlights(plan),
        "editable_spreadsheet_rows": _editable_rowset((plan.plan_json or {}).get("spreadsheet_model", []), spreadsheet_fields),
        "editable_gantt_rows": _editable_rowset((plan.plan_json or {}).get("gantt_data", []), gantt_fields),
        "spreadsheet_fields": spreadsheet_fields,
        "gantt_fields": gantt_fields,
        "sales_expectation": dict((plan.report_json or {}).get("sales_expectation", {}) or {}),
        "latest_log": plan.llm_logs.order_by("-created_at").first(),
        "edit_form": edit_form,
        "source_plans": source_plans,
        "next_plan_links": next_plan_links,
        "is_async_pending": plan.status in {"queued", "running"},
        "generation_error": (plan.report_json or {}).get("generation_error", ""),
        "async_task_meta": dict((plan.report_json or {}).get("async_task", {}) or {}),
    }
    logger.info(
        "Marketing plan detail context ready plan_id=%s elapsed_ms=%s sections=%s spreadsheet_rows=%s gantt_rows=%s",
        plan.pk,
        int((time.perf_counter() - detail_started_at) * 1000),
        len(context["plan_sections"]),
        len(context["editable_spreadsheet_rows"]),
        len(context["editable_gantt_rows"]),
    )
    return render(request, "medstratix/marketing_plan_detail.html", context)


@login_required
def marketing_plan_status(request, pk):
    plan = get_object_or_404(MarketingPlan, pk=pk)
    payload = {
        "id": plan.pk,
        "status": plan.status,
        "title": plan.title,
        "updated_at": plan.updated_at.isoformat(),
        "generation_error": (plan.report_json or {}).get("generation_error", ""),
        "async_task": dict((plan.report_json or {}).get("async_task", {}) or {}),
        "has_content": bool(plan.plan_json),
        "detail_url": reverse_lazy("medstratix:marketing_plan_detail", kwargs={"pk": plan.pk}),
    }
    return JsonResponse(payload)


@login_required
def marketing_plan_gantt(request, pk):
    plan = get_object_or_404(MarketingPlan, pk=pk)
    gantt_rows = list((plan.plan_json or {}).get("gantt_data", []) or [])
    phases = []
    status_counts: dict[str, int] = {}
    for row in gantt_rows:
        phase = stringify_plan_value(row.get("phase") or "Execution")
        if phase not in phases:
            phases.append(phase)
    phase_index = {phase: index + 1 for index, phase in enumerate(phases)}

    rows = []
    for row in gantt_rows:
        phase = stringify_plan_value(row.get("phase") or "Execution")
        status_signal = stringify_plan_value(row.get("status_signal") or "Planned")
        status_key = status_signal.lower().strip()
        status_class = "planned"
        if any(token in status_key for token in ("progress", "active", "running")):
            status_class = "active"
        elif any(token in status_key for token in ("done", "complete", "closed")):
            status_class = "done"
        elif any(token in status_key for token in ("risk", "delay", "blocked")):
            status_class = "risk"
        status_counts[status_class] = status_counts.get(status_class, 0) + 1
        rows.append(
            {
                "task": stringify_plan_value(row.get("task") or "Untitled task"),
                "phase": phase,
                "owner": stringify_plan_value(row.get("owner") or "Unassigned"),
                "start_period": stringify_plan_value(row.get("start_period") or "TBD"),
                "end_period": stringify_plan_value(row.get("end_period") or "TBD"),
                "dependency": stringify_plan_value(row.get("dependency") or ""),
                "status_signal": status_signal,
                "status_class": status_class,
                "phase_col": phase_index.get(phase, 1),
            }
        )

    context = {
        "page_title": f"{plan.title} Gantt",
        "plan": plan,
        "plan_style_label": MARKETING_PLAN_STYLE_LABELS.get(plan.output_style, plan.output_style),
        "gantt_rows": rows,
        "gantt_phases": phases or ["Execution"],
        "gantt_status_counts": {
            "planned": status_counts.get("planned", 0),
            "active": status_counts.get("active", 0),
            "done": status_counts.get("done", 0),
            "risk": status_counts.get("risk", 0),
        },
    }
    return render(request, "medstratix/marketing_plan_gantt.html", context)


@login_required
def marketing_plan_export(request, pk, fmt):
    plan = get_object_or_404(
        MarketingPlan.objects.select_related("market_account", "comparison_run").prefetch_related("llm_logs"),
        pk=pk,
    )
    latest_log = plan.llm_logs.order_by("-created_at").first()
    export_format = (fmt or "").lower().strip()
    filename = _marketing_plan_export_filename(plan, export_format)

    if export_format == "json":
        response = JsonResponse(plan.plan_json or {}, json_dumps_params={"indent": 2})
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    if export_format == "csv":
        csv_buffer = build_marketing_plan_csv(plan)
        response = HttpResponse(csv_buffer.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    if export_format == "xlsx":
        workbook_bytes = build_marketing_plan_xlsx(plan)
        response = HttpResponse(
            workbook_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    if export_format == "docx":
        document_buffer = build_marketing_plan_docx(plan, latest_log)
        response = HttpResponse(
            document_buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    if export_format == "pdf":
        pdf_buffer = build_marketing_plan_pdf(plan, latest_log)
        response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    messages.error(request, "Unsupported export format.")
    return redirect("medstratix:marketing_plan_detail", pk=plan.pk)


@login_required
def market_workspace(request):
    account_form = MarketAccountForm(prefix="account")
    stakeholder_form = MarketStakeholderForm(prefix="stakeholder")

    if request.method == "POST":
        action = request.POST.get("market_action", "").strip()
        if action == "account":
            account_form = MarketAccountForm(request.POST, prefix="account")
            if account_form.is_valid():
                account = account_form.save()
                messages.success(request, f"Market account saved: {account.name}")
                return redirect("medstratix:market_workspace")
        elif action == "stakeholder":
            stakeholder_form = MarketStakeholderForm(request.POST, prefix="stakeholder")
            if stakeholder_form.is_valid():
                stakeholder = stakeholder_form.save()
                messages.success(request, f"Stakeholder saved: {stakeholder.name}")
                return redirect("medstratix:market_workspace")

    accounts = MarketAccount.objects.prefetch_related("stakeholders").order_by("name")
    context = {
        "page_title": "Market Intelligence",
        "account_form": account_form,
        "stakeholder_form": stakeholder_form,
        "accounts": [_market_snapshot(account) for account in accounts],
    }
    return render(request, "medstratix/market_workspace.html", context)


@login_required
def strategy_detail(request, pk):
    report = get_object_or_404(
        StrategyReport.objects.select_related("your_panel", "competitor_panel", "guideline_document", "market_account").prefetch_related("llm_logs"),
        pk=pk,
    )
    context = {
        "page_title": report.title or f"Strategy {report.pk}",
        "report": report,
        "latest_log": report.llm_logs.order_by("-created_at").first(),
    }
    return render(request, "medstratix/strategy_detail.html", context)


@login_required
def strategy_export(request, pk, fmt):
    report = get_object_or_404(
        StrategyReport.objects.select_related("your_panel__company", "competitor_panel__company", "market_account").prefetch_related("llm_logs"),
        pk=pk,
    )
    latest_log = report.llm_logs.order_by("-created_at").first()
    payload = _strategy_export_payload(report, latest_log)
    export_format = (fmt or "").lower().strip()
    filename = _strategy_export_filename(report, export_format)

    if export_format == "json":
        response = JsonResponse(payload, json_dumps_params={"indent": 2})
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    if export_format == "txt":
        response = HttpResponse(_strategy_export_text(payload), content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    if export_format == "html":
        response = render(
            request,
            "medstratix/strategy_export.html",
            {
                "page_title": report.title or f"Strategy {report.pk}",
                "report": report,
                "latest_log": latest_log,
            },
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    if export_format == "docx":
        document_buffer = build_strategy_docx(report, latest_log)
        response = HttpResponse(
            document_buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    messages.error(request, "Unsupported export format.")
    return redirect("medstratix:strategy_detail", pk=report.pk)


@login_required
def run_guideline_extraction(request, pk):
    if request.method != "POST":
        return redirect("medstratix:guideline_workspace")

    guideline = get_object_or_404(GuidelineDocument, pk=pk)

    try:
        result = process_guideline_document(guideline)
        messages.success(
            request,
            f"Processing complete for {guideline.name}. "
            f"Profile: {result['parser_family']} / {result['molecular_style']}. "
            f"Created {result['sections_created']} sections, "
            f"{result['biomarker_definitions_created']} biomarkers, and "
            f"{result['therapy_rules_created']} therapy rules.",
        )
    except Exception as exc:
        messages.error(
            request,
            f"Processing failed for {guideline.name}: {exc}",
        )

    return redirect("medstratix:guideline_workspace")


@login_required
def guideline_detail(request, pk):
    guideline = get_object_or_404(GuidelineDocument, pk=pk)
    selected_section_id = request.GET.get("selected_section", "").strip()
    sections = guideline.sections.order_by("page_start", "title")
    ordered_sections = list(sections)
    section_page_lookup = {
        section.pk: (index // 12) + 1
        for index, section in enumerate(ordered_sections)
    }
    section_paginator = Paginator(sections, 12)
    section_page_obj = section_paginator.get_page(request.GET.get("sections_page"))
    parser_profile = get_parser_profile(
        guideline.name,
        guideline.cancer_type,
        [section.section_code for section in sections if section.section_code],
    )
    snapshot = _guideline_snapshot(guideline)
    biomarker_definitions = list(
        guideline.biomarker_definitions.select_related("gene")
        .prefetch_related(
            Prefetch(
                "variant_rules",
                queryset=guideline.biomarker_variant_rules.select_related(
                    "biomarker_definition__gene",
                    "source_section",
                ).order_by("variant_label"),
            ),
            Prefetch(
                "testing_method_rules",
                queryset=guideline.testing_method_rules.select_related(
                    "biomarker_definition__gene",
                    "source_section",
                ).order_by("preferred_rank", "method_type"),
            ),
        )
        .order_by("priority_rank", "gene__symbol")
    )
    therapy_rules = list(
        guideline.therapy_rules.select_related(
            "therapy_definition",
            "biomarker_variant_rule",
            "source_section",
        ).order_by("therapy_definition__name")
    )
    variant_rules = list(
        guideline.biomarker_variant_rules.select_related("biomarker_definition__gene", "source_section")
        .prefetch_related(
            Prefetch(
                "therapy_rules",
                queryset=guideline.therapy_rules.select_related(
                    "therapy_definition",
                    "source_section",
                ).order_by("therapy_definition__name"),
            )
        )
        .order_by("biomarker_definition__gene__symbol", "variant_label")
    )
    testing_rules = list(
        guideline.testing_method_rules.select_related("biomarker_definition__gene", "source_section").order_by(
            "biomarker_definition__gene__symbol", "preferred_rank"
        )
    )
    _attach_source_pages(variant_rules, section_page_lookup)
    _attach_source_pages(testing_rules, section_page_lookup)
    _attach_source_pages(therapy_rules, section_page_lookup)
    for biomarker in biomarker_definitions:
        _attach_source_pages(biomarker.variant_rules.all(), section_page_lookup)
        _attach_source_pages(biomarker.testing_method_rules.all(), section_page_lookup)
    for variant_rule in variant_rules:
        _attach_source_pages(variant_rule.therapy_rules.all(), section_page_lookup)

    pathway_summary = {
        "top_biomarkers": [biomarker.gene.symbol for biomarker in biomarker_definitions[:5]],
        "top_methods": list(dict.fromkeys(rule.get_method_type_display() for rule in testing_rules[:6])),
        "top_therapies": list(dict.fromkeys(rule.therapy_definition.name for rule in therapy_rules[:6])),
        "source_links": sum(
            1
            for collection in (variant_rules, testing_rules, therapy_rules)
            for item in collection
            if getattr(item, "source_section", None)
        ),
    }

    context = {
        "page_title": guideline.name,
        "guideline": guideline,
        "sections": list(section_page_obj.object_list),
        "section_page_obj": section_page_obj,
        "parser_profile": parser_profile,
        "snapshot": snapshot,
        "biomarker_definitions": biomarker_definitions,
        "variant_rules": variant_rules,
        "therapy_rules": therapy_rules,
        "testing_rules": testing_rules,
        "pathway_summary": pathway_summary,
        "selected_section_id": selected_section_id,
        "section_type_counts": {
            "biomarker": sections.filter(section_type="biomarker").count(),
            "testing": sections.filter(section_type="testing").count(),
            "therapy": sections.filter(section_type="therapy").count(),
            "discussion": sections.filter(section_type="discussion").count(),
        },
    }
    return render(request, "medstratix/guideline_detail.html", context)


@login_required
def run_guideline_structuring(request, pk):
    if request.method != "POST":
        return redirect("medstratix:guideline_detail", pk=pk)

    guideline = get_object_or_404(GuidelineDocument, pk=pk)

    try:
        result = process_guideline_document(guideline)
        messages.success(
            request,
            f"Processing complete for {guideline.name}. "
            f"Profile: {result['parser_family']} / {result['molecular_style']}. "
            f"Created {result['sections_created']} sections, "
            f"{result['biomarker_definitions_created']} biomarkers, and "
            f"{result['therapy_rules_created']} therapy rules.",
        )
    except Exception as exc:
        messages.error(
            request,
            f"Processing failed for {guideline.name}: {exc}",
        )

    return redirect("medstratix:guideline_detail", pk=pk)


@login_required
def guideline_dashboard(request):
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    depth_filter = request.GET.get("depth", "").strip()
    sort_by = request.GET.get("sort", "depth")

    guidelines = GuidelineDocument.objects.all()
    if search_query:
        guidelines = guidelines.filter(
            Q(name__icontains=search_query)
            | Q(cancer_type__icontains=search_query)
            | Q(version__icontains=search_query)
        )
    if status_filter:
        guidelines = guidelines.filter(status=status_filter)
    guidelines = guidelines.order_by("cancer_type", "name")
    snapshots = [_guideline_snapshot(guideline) for guideline in guidelines]
    if depth_filter:
        snapshots = [item for item in snapshots if item["depth_label"].lower() == depth_filter.lower()]

    depth_order = {"Deep": 0, "Starter": 1, "Light": 2}
    dashboard_sort_map = {
        "depth": lambda item: (depth_order[item["depth_label"]], item["guideline"].cancer_type.lower(), item["guideline"].name.lower()),
        "name": lambda item: (item["guideline"].name.lower(),),
        "cancer": lambda item: (item["guideline"].cancer_type.lower(), item["guideline"].name.lower()),
        "biomarkers": lambda item: (-item["biomarkers"], item["guideline"].name.lower()),
        "testing": lambda item: (-item["testing"], item["guideline"].name.lower()),
        "therapies": lambda item: (-item["therapies"], item["guideline"].name.lower()),
        "sections": lambda item: (-item["sections"], item["guideline"].name.lower()),
    }
    snapshots.sort(key=dashboard_sort_map.get(sort_by, dashboard_sort_map["depth"]))
    paginator = Paginator(snapshots, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    current_items = list(page_obj.object_list)
    deep_count = sum(1 for item in snapshots if item["depth_label"] == "Deep")
    starter_count = sum(1 for item in snapshots if item["depth_label"] == "Starter")
    light_count = sum(1 for item in snapshots if item["depth_label"] == "Light")

    context = {
        "page_title": "Guideline Dashboard",
        "snapshots": current_items,
        "page_obj": page_obj,
        "lowest_depth": [item for item in snapshots if item["depth_label"] != "Deep"][:6],
        "filters": {
            "q": search_query,
            "status": status_filter,
            "depth": depth_filter,
            "sort": sort_by,
            "query_suffix": _query_without_page(request),
        },
        "active_filter_chips": _active_filter_chips(
            {"q": search_query, "status": status_filter, "depth": depth_filter, "sort": sort_by},
            reverse_lazy("medstratix:guideline_dashboard"),
        ),
        "sort_links": {
            "name": _build_query_string(
                {"q": search_query, "status": status_filter, "depth": depth_filter, "sort": sort_by},
                sort="name",
            ),
            "cancer": _build_query_string(
                {"q": search_query, "status": status_filter, "depth": depth_filter, "sort": sort_by},
                sort="cancer",
            ),
            "sections": _build_query_string(
                {"q": search_query, "status": status_filter, "depth": depth_filter, "sort": sort_by},
                sort="sections",
            ),
            "biomarkers": _build_query_string(
                {"q": search_query, "status": status_filter, "depth": depth_filter, "sort": sort_by},
                sort="biomarkers",
            ),
            "testing": _build_query_string(
                {"q": search_query, "status": status_filter, "depth": depth_filter, "sort": sort_by},
                sort="testing",
            ),
            "therapies": _build_query_string(
                {"q": search_query, "status": status_filter, "depth": depth_filter, "sort": sort_by},
                sort="therapies",
            ),
            "profile": _build_query_string(
                {"q": search_query, "status": status_filter, "depth": depth_filter, "sort": sort_by},
                sort="name",
            ),
            "depth": _build_query_string(
                {"q": search_query, "status": status_filter, "depth": depth_filter, "sort": sort_by},
                sort="depth",
            ),
        },
        "summary": {
            "total": len(snapshots),
            "reviewed": sum(1 for item in snapshots if item["guideline"].status == "reviewed"),
            "deep": deep_count,
            "starter": starter_count,
            "light": light_count,
            "total_biomarkers": sum(item["biomarkers"] for item in snapshots),
            "total_therapies": sum(item["therapies"] for item in snapshots),
            "total_testing": sum(item["testing"] for item in snapshots),
        },
    }
    return render(request, "medstratix/guideline_dashboard.html", context)


@login_required
def testing_panels(request):
    panel_specs = [
        {"title": "DNA NGS Based Gene Panels", "eyebrow": "DNA NGS", "method_type": TestingMethodType.DNA_NGS},
        {"title": "RNA NGS Based Gene Panels", "eyebrow": "RNA NGS", "method_type": TestingMethodType.RNA_NGS},
        {"title": "Plasma Testing Gene Panels", "eyebrow": "Plasma Testing", "method_type": TestingMethodType.PLASMA},
        {"title": "IHC Based Testing Panels", "eyebrow": "IHC", "method_type": TestingMethodType.IHC},
    ]

    panels = []
    total_diseases = 0
    total_genes = 0
    for spec in panel_specs:
        summary = _aggregate_testing_panel(spec["method_type"])
        panels.append({**spec, **summary})
        total_diseases += summary["disease_count"]
        total_genes += summary["gene_total"]

    context = {
        "page_title": "Testing Panels",
        "panels": panels,
        "summary": {
            "total_methods": len(panels),
            "total_diseases": total_diseases,
            "total_genes": total_genes,
        },
    }
    return render(request, "medstratix/testing_panels.html", context)


@login_required
def therapy_panels(request):
    panel = _aggregate_therapy_panel()
    context = {
        "page_title": "Therapy Rules",
        "panel": panel,
        "summary": {
            "disease_buckets": panel["disease_count"],
            "total_therapy_entries": panel["therapy_total"],
            "unique_therapies": panel["unique_therapy_count"],
        },
    }
    return render(request, "medstratix/therapy_panels.html", context)


@login_required
def biomarker_catalog(request):
    search_query = request.GET.get("q", "").strip()
    catalog = _aggregate_biomarker_catalog(search_query)
    paginator = Paginator(catalog["diseases"], 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_title": "Biomarker Catalog",
        "catalog": {**catalog, "diseases": list(page_obj.object_list)},
        "page_obj": page_obj,
        "filters": {
            "q": search_query,
            "query_suffix": _query_without_page(request),
        },
        "active_filter_chips": _active_filter_chips(
            {"q": search_query},
            reverse_lazy("medstratix:biomarker_catalog"),
        ),
        "summary": {
            "disease_buckets": catalog["disease_count"],
            "total_gene_entries": catalog["gene_total"],
            "total_variant_entries": catalog["variant_total"],
            "unique_genes": catalog["unique_gene_count"],
            "unique_variants": catalog["unique_variant_count"],
        },
    }
    return render(request, "medstratix/biomarker_catalog.html", context)
