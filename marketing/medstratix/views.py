from collections import defaultdict
import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from urllib.parse import urlencode
from .forms import (
    GuidelineUploadForm,
    MarketAccountForm,
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
    GuidelineDocument,
    GuidelineTherapyRule,
    LLMGenerationLog,
    MarketAccount,
    MarketStakeholder,
    Panel,
    SampleType,
    StrategyReport,
    TestingMethodRule,
    TestingMethodType,
)
from .services.guideline_pipeline import process_guideline_document
from .services.nccn_profiles import get_parser_profile
from .services.panel_comparison import build_comparison_bundle
from .services.panel_upload import save_uploaded_panel
from .services.strategy_generator import generate_structured_strategy


logger = logging.getLogger("medstratix.views")


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
    }


def _panel_initial(panel: Panel) -> dict:
    gene_text = "\n".join(
        panel.panel_genes.select_related("gene").order_by("gene__symbol").values_list("gene__symbol", flat=True)
    )
    return {
        "company_name": panel.company.name,
        "panel_name": panel.name,
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
    }


def _selected_market_accounts(market_accounts: list[MarketAccount], selected_ids: list[str]) -> list[MarketAccount]:
    selected_id_set = {item.strip() for item in selected_ids if item.strip().isdigit()}
    return [account for account in market_accounts if str(account.pk) in selected_id_set]


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
                f"Loaded {result['gene_count']} genes. {result['price_note']}",
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
            messages.success(request, f"{result['panel'].name} updated successfully. {result['price_note']}")
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
            selected_your_panel = form.cleaned_data["your_panel"]
            selected_competitors = list(form.cleaned_data["competitor_panels"])
            if not selected_competitors:
                messages.error(request, "Choose at least one competitor panel for comparison.")
            else:
                return redirect(
                    f"{reverse_lazy('medstratix:panel_compare_result')}"
                    f"?your_panel={selected_your_panel.pk}&competitors={_serialize_competitor_ids(selected_competitors)}"
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
    your_panel_id = request.GET.get("your_panel", "").strip()
    competitor_ids = _parse_competitor_ids(request.GET.get("competitors", ""))
    disease_filter = request.GET.get("disease", "").strip()

    if not your_panel_id.isdigit() or not competitor_ids:
        messages.error(request, "Select one of your panels and at least one competitor panel to view results.")
        return redirect("medstratix:panel_compare_setup")

    your_panel = get_object_or_404(Panel.objects.select_related("company"), pk=int(your_panel_id), company__type=CompanyType.YOURS)
    competitor_panels = list(
        Panel.objects.select_related("company")
        .filter(pk__in=competitor_ids, company__type=CompanyType.COMPETITOR)
        .order_by("company__name", "name")
    )
    if not competitor_panels:
        messages.error(request, "No competitor panels were found for this comparison.")
        return redirect("medstratix:panel_compare_setup")

    comparison_bundle = build_comparison_bundle(your_panel, competitor_panels)
    market_accounts = list(MarketAccount.objects.prefetch_related("stakeholders").order_by("name"))
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
    if request.method == "POST":
        competitor_panel_id = request.POST.get("competitor_panel_id", "").strip()
        selected_market_account_ids = request.POST.getlist("market_account_ids")
        target_competitor = next((panel for panel in competitor_panels if str(panel.pk) == competitor_panel_id), None)
        selected_accounts = _selected_market_accounts(market_accounts, selected_market_account_ids)
        primary_account = selected_accounts[0] if selected_accounts else None
        selected_stakeholders = []
        for account in selected_accounts:
            selected_stakeholders.extend(list(account.stakeholders.all()))
        if target_competitor:
            logger.info(
                "Strategy generation requested your_panel=%s competitor_panel=%s disease_filter=%s market_accounts=%s",
                your_panel.name,
                target_competitor.name,
                disease_filter or "ALL",
                [account.name for account in selected_accounts],
            )
            competitor_bundle = next(
                (payload for payload in comparison_bundle["competitor_guideline_coverages"] if payload["panel"].pk == target_competitor.pk),
                None,
            )
            comparison_pair = next(
                (payload for payload in comparison_bundle["competitor_comparisons"] if payload["competitor_panel"].pk == target_competitor.pk),
                None,
            )
            try:
                strategy_result = generate_structured_strategy(
                    your_panel=your_panel,
                    competitor_panel=target_competitor,
                    comparison_pair=comparison_pair,
                    your_guideline_coverage=comparison_bundle["your_guideline_coverage"],
                    competitor_guideline_coverage=competitor_bundle,
                    disease_filter=disease_filter,
                    market_accounts=selected_accounts,
                    stakeholders=selected_stakeholders,
                )
                strategy_payload = strategy_result["response_json"]
                strategy_record = StrategyReport.objects.create(
                    your_panel=your_panel,
                    competitor_panel=target_competitor,
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
                            "your_panel": your_panel.pk,
                            "competitors": competitor_ids,
                        },
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
                    your_panel.name,
                    target_competitor.name,
                )
                messages.success(request, f"Strategy draft generated for {target_competitor.name}.")
                strategy_outputs.append(
                    {
                        "competitor_panel": target_competitor,
                        "strategy_text": strategy_payload.get("executive_summary", ""),
                        "report_id": strategy_record.pk,
                        "title": strategy_record.title,
                    }
                )
            except Exception as exc:
                logger.exception(
                    "Strategy generation failed your_panel=%s competitor_panel=%s disease_filter=%s",
                    your_panel.name,
                    target_competitor.name,
                    disease_filter or "ALL",
                )
                messages.error(request, f"Strategy generation failed for {target_competitor.name}: {exc}")

    existing_strategy_reports = list(
        StrategyReport.objects.filter(
            your_panel=your_panel,
            competitor_panel__in=competitor_panels,
        )
        .select_related("competitor_panel")
        .order_by("-created_at")[:8]
    )

    context = {
        "page_title": "Panel Comparison Results",
        "your_panel": your_panel,
        "competitor_panels": competitor_panels,
        "grouped_competitors": grouped_competitors,
        "comparison_bundle": comparison_bundle,
        "market_accounts": market_accounts,
        "filters": {
            "disease": disease_filter,
            "your_panel": your_panel.pk,
            "competitors": _serialize_competitor_ids(competitor_panels),
        },
        "disease_choices": disease_choices,
        "strategy_outputs": strategy_outputs,
        "existing_strategy_reports": existing_strategy_reports,
        "selected_market_account_ids": selected_market_account_ids,
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
