from collections import defaultdict

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from urllib.parse import urlencode
from .forms import GuidelineUploadForm, SignInForm, SignUpForm
from .models import GuidelineDocument, GuidelineTherapyRule, TestingMethodRule, TestingMethodType
from .services.guideline_pipeline import process_guideline_document
from .services.nccn_profiles import get_parser_profile


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


def _active_filter_chips(filters: dict, base_route: str) -> list[dict]:
    labels = {
        "q": "Search",
        "status": "Status",
        "depth": "Depth",
        "sort": "Sort",
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
    sections = guideline.sections.order_by("page_start", "title")
    section_paginator = Paginator(sections, 12)
    section_page_obj = section_paginator.get_page(request.GET.get("sections_page"))
    parser_profile = get_parser_profile(
        guideline.name,
        guideline.cancer_type,
        [section.section_code for section in sections if section.section_code],
    )
    snapshot = _guideline_snapshot(guideline)
    biomarker_definitions = list(
        guideline.biomarker_definitions.select_related("gene").order_by("priority_rank", "gene__symbol")
    )
    therapy_rules = list(
        guideline.therapy_rules.select_related("therapy_definition", "biomarker_variant_rule").order_by(
            "therapy_definition__name"
        )
    )
    testing_rules = list(
        guideline.testing_method_rules.select_related("biomarker_definition__gene").order_by(
            "biomarker_definition__gene__symbol", "preferred_rank"
        )
    )

    context = {
        "page_title": guideline.name,
        "guideline": guideline,
        "sections": list(section_page_obj.object_list),
        "section_page_obj": section_page_obj,
        "parser_profile": parser_profile,
        "snapshot": snapshot,
        "biomarker_definitions": biomarker_definitions,
        "therapy_rules": therapy_rules,
        "testing_rules": testing_rules,
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
