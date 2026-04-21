from django.contrib import admin

from .models import (
    BiomarkerDefinition,
    BiomarkerVariantRule,
    Company,
    ComparisonReport,
    Gene,
    GuidelineDocument,
    GuidelineSection,
    GuidelineTherapyRule,
    LLMGenerationLog,
    MarketAccount,
    MarketStakeholder,
    MolecularProfile,
    Panel,
    PanelGene,
    PanelGuidelineGeneMatch,
    PanelGuidelineMatch,
    StrategyReport,
    TestingMethodRule,
    TherapyDefinition,
)


class PanelGeneInline(admin.TabularInline):
    model = PanelGene
    extra = 0
    autocomplete_fields = ["gene"]


class GuidelineSectionInline(admin.TabularInline):
    model = GuidelineSection
    extra = 0
    fields = ["section_code", "title", "section_type", "page_start", "page_end"]
    show_change_link = True


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "created_at"]
    list_filter = ["type"]
    search_fields = ["name"]


@admin.register(MarketAccount)
class MarketAccountAdmin(admin.ModelAdmin):
    list_display = ["name", "institution_type", "city", "decision_style", "market_corruption_pressure", "created_at"]
    list_filter = ["institution_type", "decision_style", "market_corruption_pressure", "referral_distortion_risk"]
    search_fields = ["name", "city", "disease_focus", "notes"]


@admin.register(MarketStakeholder)
class MarketStakeholderAdmin(admin.ModelAdmin):
    list_display = ["name", "account", "role", "specialty", "influence_level", "created_at"]
    list_filter = ["role", "influence_level", "evidence_preference", "conference_interest"]
    search_fields = ["name", "account__name", "specialty", "behavioral_notes"]
    autocomplete_fields = ["account"]


@admin.register(Gene)
class GeneAdmin(admin.ModelAdmin):
    list_display = ["symbol", "created_at"]
    search_fields = ["symbol"]


@admin.register(Panel)
class PanelAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "price", "tat", "created_at"]
    list_filter = ["company"]
    search_fields = ["name", "company__name"]
    autocomplete_fields = ["company"]
    inlines = [PanelGeneInline]


@admin.register(PanelGene)
class PanelGeneAdmin(admin.ModelAdmin):
    list_display = ["panel", "gene", "created_at"]
    search_fields = ["panel__name", "gene__symbol"]
    autocomplete_fields = ["panel", "gene"]


@admin.register(ComparisonReport)
class ComparisonReportAdmin(admin.ModelAdmin):
    list_display = ["panel_a", "panel_b", "overlap_count", "unique_a_count", "unique_b_count", "created_at"]
    search_fields = ["panel_a__name", "panel_b__name"]
    autocomplete_fields = ["panel_a", "panel_b"]


@admin.register(GuidelineDocument)
class GuidelineDocumentAdmin(admin.ModelAdmin):
    list_display = ["name", "cancer_type", "version", "year", "status", "published_at"]
    list_filter = ["status", "cancer_type", "year"]
    search_fields = ["name", "cancer_type", "version"]
    prepopulated_fields = {"slug": ["cancer_type", "name", "version"]}
    inlines = [GuidelineSectionInline]


@admin.register(GuidelineSection)
class GuidelineSectionAdmin(admin.ModelAdmin):
    list_display = ["title", "guideline_document", "section_code", "section_type", "page_start", "page_end"]
    list_filter = ["section_type", "guideline_document"]
    search_fields = ["title", "section_code", "raw_text", "normalized_text"]
    autocomplete_fields = ["guideline_document"]


@admin.register(MolecularProfile)
class MolecularProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "guideline_document", "cancer_type", "is_active"]
    list_filter = ["is_active", "cancer_type"]
    search_fields = ["name", "cancer_type", "description"]
    autocomplete_fields = ["guideline_document"]


@admin.register(BiomarkerDefinition)
class BiomarkerDefinitionAdmin(admin.ModelAdmin):
    list_display = ["gene", "guideline_document", "molecular_profile", "alteration_family", "is_actionable", "priority_rank"]
    list_filter = ["alteration_family", "is_actionable", "guideline_document"]
    search_fields = ["gene__symbol", "description"]
    autocomplete_fields = ["guideline_document", "molecular_profile", "gene"]


@admin.register(BiomarkerVariantRule)
class BiomarkerVariantRuleAdmin(admin.ModelAdmin):
    list_display = ["variant_label", "biomarker_definition", "stage_context", "line_of_therapy", "is_preferred"]
    list_filter = ["is_preferred", "guideline_document", "stage_context", "line_of_therapy"]
    search_fields = ["variant_label", "variant_type", "notes", "biomarker_definition__gene__symbol"]
    autocomplete_fields = ["guideline_document", "biomarker_definition", "source_section"]


@admin.register(TestingMethodRule)
class TestingMethodRuleAdmin(admin.ModelAdmin):
    list_display = ["biomarker_definition", "method_type", "preferred_rank", "is_required"]
    list_filter = ["method_type", "is_required", "guideline_document"]
    search_fields = ["biomarker_definition__gene__symbol", "notes"]
    autocomplete_fields = ["guideline_document", "biomarker_definition", "source_section"]


@admin.register(TherapyDefinition)
class TherapyDefinitionAdmin(admin.ModelAdmin):
    list_display = ["name", "therapy_class", "is_systemic"]
    list_filter = ["is_systemic", "therapy_class"]
    search_fields = ["name", "therapy_class", "manufacturer"]


@admin.register(GuidelineTherapyRule)
class GuidelineTherapyRuleAdmin(admin.ModelAdmin):
    list_display = ["therapy_definition", "biomarker_variant_rule", "therapy_line", "therapy_role", "guideline_document"]
    list_filter = ["therapy_role", "therapy_line", "guideline_document"]
    search_fields = [
        "therapy_definition__name",
        "biomarker_variant_rule__variant_label",
        "special_notes",
    ]
    autocomplete_fields = [
        "guideline_document",
        "molecular_profile",
        "biomarker_variant_rule",
        "therapy_definition",
        "source_section",
    ]


@admin.register(StrategyReport)
class StrategyReportAdmin(admin.ModelAdmin):
    list_display = ["title", "your_panel", "competitor_panel", "market_account", "disease_focus", "llm_model", "created_at"]
    search_fields = ["title", "your_panel__name", "competitor_panel__name", "guideline_document__name", "disease_focus", "market_account__name"]
    autocomplete_fields = ["your_panel", "competitor_panel", "guideline_document", "market_account"]


@admin.register(LLMGenerationLog)
class LLMGenerationLogAdmin(admin.ModelAdmin):
    list_display = ["strategy_report", "provider", "model_name", "status", "total_tokens", "estimated_cost_usd", "created_at"]
    list_filter = ["provider", "model_name", "status"]
    search_fields = ["strategy_report__title", "strategy_report__your_panel__name", "strategy_report__competitor_panel__name"]
    autocomplete_fields = ["strategy_report"]


@admin.register(PanelGuidelineMatch)
class PanelGuidelineMatchAdmin(admin.ModelAdmin):
    list_display = ["panel", "guideline_document", "cancer_type", "matched_genes_count", "missing_actionable_genes_count"]
    list_filter = ["cancer_type", "guideline_document"]
    search_fields = ["panel__name", "guideline_document__name"]
    autocomplete_fields = ["panel", "guideline_document"]


@admin.register(PanelGuidelineGeneMatch)
class PanelGuidelineGeneMatchAdmin(admin.ModelAdmin):
    list_display = ["panel_guideline_match", "gene", "match_type"]
    list_filter = ["match_type"]
    search_fields = ["gene__symbol", "panel_guideline_match__panel__name"]
    autocomplete_fields = ["panel_guideline_match", "gene", "biomarker_definition"]
