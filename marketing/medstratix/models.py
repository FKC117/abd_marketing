from django.conf import settings
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CompanyType(models.TextChoices):
    YOURS = "yours", "Your Company"
    COMPETITOR = "competitor", "Competitor"
    LAB = "lab", "Lab"
    GUIDELINE_BODY = "guideline_body", "Guideline Body"
    OTHER = "other", "Other"


class GuidelineStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IMPORTED = "imported", "Imported"
    EXTRACTED = "extracted", "Extracted"
    REVIEWED = "reviewed", "Reviewed"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class SectionType(models.TextChoices):
    BIOMARKER = "biomarker", "Biomarker"
    THERAPY = "therapy", "Therapy"
    TESTING = "testing", "Testing"
    DISCUSSION = "discussion", "Discussion"
    ALGORITHM = "algorithm", "Algorithm"
    OTHER = "other", "Other"


class AlterationFamily(models.TextChoices):
    MUTATION = "mutation", "Mutation"
    FUSION = "fusion", "Fusion"
    AMPLIFICATION = "amplification", "Amplification"
    EXON_SKIPPING = "exon_skipping", "Exon Skipping"
    PROTEIN_OVEREXPRESSION = "protein_overexpression", "Protein Overexpression"
    COPY_NUMBER_GAIN = "copy_number_gain", "Copy Number Gain"
    OTHER = "other", "Other"


class TestingMethodType(models.TextChoices):
    DNA_NGS = "dna_ngs", "DNA NGS"
    RNA_NGS = "rna_ngs", "RNA NGS"
    TISSUE = "tissue_testing", "Tissue Testing"
    PLASMA = "plasma_testing", "Plasma Testing"
    IHC = "ihc", "IHC"
    FISH = "fish", "FISH"
    RTPCR = "rt_pcr", "RT-PCR"
    OTHER = "other", "Other"


class TherapyRole(models.TextChoices):
    FIRST_LINE = "first_line", "First Line"
    SUBSEQUENT = "subsequent", "Subsequent"
    MAINTENANCE = "maintenance", "Maintenance"
    PREFERRED = "preferred", "Preferred"
    USEFUL_IN_CIRCUMSTANCES = "useful_in_certain_circumstances", "Useful in Certain Circumstances"
    OTHER = "other", "Other"


class MatchType(models.TextChoices):
    PRESENT_ACTIONABLE = "present_actionable", "Present Actionable"
    PRESENT_NON_ACTIONABLE = "present_non_actionable", "Present Non-Actionable"
    MISSING_ACTIONABLE = "missing_actionable", "Missing Actionable"
    INCOMPLETE_VARIANT_COVERAGE = "present_but_incomplete_for_variant_detection", "Present But Incomplete"


class SampleType(models.TextChoices):
    TISSUE = "tissue", "Tissue"
    PLASMA = "plasma", "Plasma"
    OTHER = "other", "Other"


class SensitivityLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    UNKNOWN = "unknown", "Unknown"


class DecisionStyle(models.TextChoices):
    INSTITUTION = "institution", "Institution Driven"
    DOCTOR = "doctor", "Doctor Driven"
    MIXED = "mixed", "Mixed"


class InstitutionType(models.TextChoices):
    HOSPITAL = "hospital", "Hospital"
    DIAGNOSTIC_CENTER = "diagnostic_center", "Diagnostic Center"
    CLINIC = "clinic", "Clinic"
    CHAMBER = "chamber", "Physician Chamber"
    OTHER = "other", "Other"


class StakeholderRole(models.TextChoices):
    DOCTOR = "doctor", "Doctor"
    PATHOLOGIST = "pathologist", "Pathologist"
    ONCOLOGIST = "oncologist", "Oncologist"
    PROCUREMENT = "procurement", "Procurement"
    ADMIN = "admin", "Administrator"
    LAB_MANAGER = "lab_manager", "Lab Manager"
    OTHER = "other", "Other"


class Company(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=32, choices=CompanyType.choices, default=CompanyType.OTHER)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class MarketAccount(TimeStampedModel):
    name = models.CharField(max_length=255)
    institution_type = models.CharField(max_length=64, choices=InstitutionType.choices, default=InstitutionType.OTHER)
    city = models.CharField(max_length=255, blank=True)
    decision_style = models.CharField(max_length=32, choices=DecisionStyle.choices, default=DecisionStyle.MIXED)
    disease_focus = models.CharField(max_length=255, blank=True)
    estimated_test_volume = models.CharField(max_length=255, blank=True)
    evidence_sensitivity = models.CharField(max_length=32, choices=SensitivityLevel.choices, default=SensitivityLevel.UNKNOWN)
    price_sensitivity = models.CharField(max_length=32, choices=SensitivityLevel.choices, default=SensitivityLevel.UNKNOWN)
    tat_sensitivity = models.CharField(max_length=32, choices=SensitivityLevel.choices, default=SensitivityLevel.UNKNOWN)
    conference_interest = models.BooleanField(default=False)
    education_interest = models.BooleanField(default=False)
    market_corruption_pressure = models.CharField(max_length=32, choices=SensitivityLevel.choices, default=SensitivityLevel.UNKNOWN)
    referral_distortion_risk = models.CharField(max_length=32, choices=SensitivityLevel.choices, default=SensitivityLevel.UNKNOWN)
    compliance_red_flags = models.TextField(blank=True)
    ethical_growth_goal = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MarketStakeholder(TimeStampedModel):
    account = models.ForeignKey(MarketAccount, on_delete=models.CASCADE, related_name="stakeholders")
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=64, choices=StakeholderRole.choices, default=StakeholderRole.OTHER)
    specialty = models.CharField(max_length=255, blank=True)
    influence_level = models.CharField(max_length=32, choices=SensitivityLevel.choices, default=SensitivityLevel.UNKNOWN)
    evidence_preference = models.CharField(max_length=32, choices=SensitivityLevel.choices, default=SensitivityLevel.UNKNOWN)
    conference_interest = models.BooleanField(default=False)
    service_expectation = models.TextField(blank=True)
    behavioral_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["account__name", "name"]

    def __str__(self):
        return f"{self.account.name} - {self.name}"


class Gene(TimeStampedModel):
    symbol = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["symbol"]

    def save(self, *args, **kwargs):
        self.symbol = self.symbol.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.symbol


class Panel(TimeStampedModel):
    name = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="panels")
    sample_type = models.CharField(max_length=32, choices=SampleType.choices, default=SampleType.TISSUE)
    supports_dna_ngs = models.BooleanField(default=True)
    supports_rna_ngs = models.BooleanField(default=False)
    supports_fusions = models.BooleanField(default=False)
    supports_cnv = models.BooleanField(default=False)
    supports_msi = models.BooleanField(default=False)
    supports_tmb = models.BooleanField(default=False)
    supports_ihc = models.BooleanField(default=False)
    supports_fish = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tat = models.CharField("turnaround time", max_length=100, blank=True)
    genes = models.ManyToManyField(Gene, through="PanelGene", related_name="panels")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["company", "name"], name="unique_panel_per_company"),
        ]

    def __str__(self):
        return f"{self.company.name} - {self.name}"


class PanelGene(TimeStampedModel):
    panel = models.ForeignKey(Panel, on_delete=models.CASCADE, related_name="panel_genes")
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name="panel_genes")

    class Meta:
        ordering = ["panel__name", "gene__symbol"]
        constraints = [
            models.UniqueConstraint(fields=["panel", "gene"], name="unique_gene_per_panel"),
        ]

    def __str__(self):
        return f"{self.panel.name} - {self.gene.symbol}"


class ComparisonReport(TimeStampedModel):
    panel_a = models.ForeignKey(Panel, on_delete=models.CASCADE, related_name="comparison_reports_as_a")
    panel_b = models.ForeignKey(Panel, on_delete=models.CASCADE, related_name="comparison_reports_as_b")
    overlap_count = models.PositiveIntegerField(default=0)
    unique_a_count = models.PositiveIntegerField(default=0)
    unique_b_count = models.PositiveIntegerField(default=0)
    coverage_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    report_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comparison: {self.panel_a.name} vs {self.panel_b.name}"


class ComparisonRun(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comparison_runs",
    )
    name = models.CharField(max_length=255, blank=True)
    your_panels = models.ManyToManyField(Panel, related_name="comparison_runs_as_yours")
    competitor_panels = models.ManyToManyField(Panel, related_name="comparison_runs_as_competitors")
    disease_filter = models.CharField(max_length=255, blank=True)
    summary_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or f"Comparison Run {self.pk}"


class MarketingPlan(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketing_plans",
    )
    title = models.CharField(max_length=255)
    objective = models.TextField(blank=True)
    geography = models.CharField(max_length=255, blank=True)
    disease_focus = models.CharField(max_length=255, blank=True)
    output_style = models.CharField(max_length=64, default="brief_plan")
    include_product_context = models.BooleanField(default=False)
    strategist_note = models.TextField(blank=True)
    market_account = models.ForeignKey(
        MarketAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketing_plans",
    )
    comparison_run = models.ForeignKey(
        ComparisonRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketing_plans",
    )
    status = models.CharField(max_length=64, default="draft")
    executive_summary = models.TextField(blank=True)
    llm_provider = models.CharField(max_length=100, blank=True)
    llm_model = models.CharField(max_length=100, blank=True)
    plan_json = models.JSONField(default=dict, blank=True)
    plan_text = models.TextField(blank=True)
    report_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class GuidelineDocument(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    cancer_type = models.CharField(max_length=255)
    version = models.CharField(max_length=100, blank=True)
    year = models.PositiveIntegerField(blank=True, null=True)
    source_file = models.FileField(upload_to="guidelines/", max_length=500)
    status = models.CharField(max_length=32, choices=GuidelineStatus.choices, default=GuidelineStatus.DRAFT)
    published_at = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["cancer_type", "name", "-year"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version", "year"],
                name="unique_guideline_document_version",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = f"{self.cancer_type}-{self.name}-{self.version or self.year or 'guideline'}"
            self.slug = slugify(base)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.version or self.year or 'draft'})"


class GuidelineSection(TimeStampedModel):
    guideline_document = models.ForeignKey(
        GuidelineDocument,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    section_code = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=255)
    page_start = models.PositiveIntegerField(blank=True, null=True)
    page_end = models.PositiveIntegerField(blank=True, null=True)
    raw_text = models.TextField()
    normalized_text = models.TextField(blank=True)
    section_type = models.CharField(max_length=32, choices=SectionType.choices, default=SectionType.OTHER)

    class Meta:
        ordering = ["guideline_document", "page_start", "title"]
        indexes = [
            models.Index(fields=["guideline_document", "section_code"]),
        ]

    def __str__(self):
        return self.section_code or self.title


class MolecularProfile(TimeStampedModel):
    guideline_document = models.ForeignKey(
        GuidelineDocument,
        on_delete=models.CASCADE,
        related_name="molecular_profiles",
    )
    cancer_type = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    clinical_context = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["guideline_document", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["guideline_document", "name"],
                name="unique_molecular_profile_per_guideline",
            ),
        ]

    def __str__(self):
        return self.name


class BiomarkerDefinition(TimeStampedModel):
    guideline_document = models.ForeignKey(
        GuidelineDocument,
        on_delete=models.CASCADE,
        related_name="biomarker_definitions",
    )
    cancer_type = models.CharField(max_length=255, blank=True)
    guideline_context = models.CharField(max_length=255, blank=True)
    molecular_profile = models.ForeignKey(
        MolecularProfile,
        on_delete=models.CASCADE,
        related_name="biomarker_definitions",
    )
    gene = models.ForeignKey(Gene, on_delete=models.PROTECT, related_name="biomarker_definitions")
    alias_json = models.JSONField(default=list, blank=True)
    alteration_family = models.CharField(max_length=32, choices=AlterationFamily.choices)
    description = models.TextField(blank=True)
    is_actionable = models.BooleanField(default=False)
    priority_rank = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["guideline_document", "priority_rank", "gene__symbol"]
        constraints = [
            models.UniqueConstraint(
                fields=["guideline_document", "molecular_profile", "gene", "alteration_family"],
                name="unique_biomarker_definition_per_guideline_profile",
            ),
        ]

    def __str__(self):
        return f"{self.gene.symbol} ({self.alteration_family})"


class BiomarkerVariantRule(TimeStampedModel):
    guideline_document = models.ForeignKey(
        GuidelineDocument,
        on_delete=models.CASCADE,
        related_name="biomarker_variant_rules",
    )
    cancer_type = models.CharField(max_length=255, blank=True)
    guideline_context = models.CharField(max_length=255, blank=True)
    biomarker_definition = models.ForeignKey(
        BiomarkerDefinition,
        on_delete=models.CASCADE,
        related_name="variant_rules",
    )
    variant_label = models.CharField(max_length=255)
    variant_type = models.CharField(max_length=100, blank=True)
    variant_details_json = models.JSONField(default=dict, blank=True)
    testing_context = models.TextField(blank=True)
    histology_context = models.CharField(max_length=255, blank=True)
    stage_context = models.CharField(max_length=255, blank=True)
    disease_setting = models.CharField(max_length=255, blank=True)
    line_of_therapy = models.CharField(max_length=100, blank=True)
    is_preferred = models.BooleanField(default=False)
    evidence_level = models.CharField(max_length=100, blank=True)
    recommendation_category = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    source_section = models.ForeignKey(
        GuidelineSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="variant_rules",
    )

    class Meta:
        ordering = ["biomarker_definition__gene__symbol", "variant_label"]
        indexes = [
            models.Index(fields=["stage_context", "line_of_therapy"]),
        ]

    def __str__(self):
        return self.variant_label


class TestingMethodRule(TimeStampedModel):
    guideline_document = models.ForeignKey(
        GuidelineDocument,
        on_delete=models.CASCADE,
        related_name="testing_method_rules",
    )
    cancer_type = models.CharField(max_length=255, blank=True)
    guideline_context = models.CharField(max_length=255, blank=True)
    biomarker_definition = models.ForeignKey(
        BiomarkerDefinition,
        on_delete=models.CASCADE,
        related_name="testing_method_rules",
    )
    method_type = models.CharField(max_length=32, choices=TestingMethodType.choices)
    preferred_rank = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    source_section = models.ForeignKey(
        GuidelineSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="testing_method_rules",
    )

    class Meta:
        ordering = ["biomarker_definition__gene__symbol", "preferred_rank"]

    def __str__(self):
        return f"{self.biomarker_definition} - {self.method_type}"


class TherapyDefinition(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    therapy_class = models.CharField(max_length=255, blank=True)
    combination_json = models.JSONField(default=list, blank=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    is_systemic = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GuidelineTherapyRule(TimeStampedModel):
    guideline_document = models.ForeignKey(
        GuidelineDocument,
        on_delete=models.CASCADE,
        related_name="therapy_rules",
    )
    cancer_type = models.CharField(max_length=255, blank=True)
    guideline_context = models.CharField(max_length=255, blank=True)
    molecular_profile = models.ForeignKey(
        MolecularProfile,
        on_delete=models.CASCADE,
        related_name="therapy_rules",
    )
    biomarker_variant_rule = models.ForeignKey(
        BiomarkerVariantRule,
        on_delete=models.CASCADE,
        related_name="therapy_rules",
    )
    therapy_definition = models.ForeignKey(
        TherapyDefinition,
        on_delete=models.CASCADE,
        related_name="guideline_rules",
    )
    therapy_line = models.CharField(max_length=100, blank=True)
    therapy_role = models.CharField(max_length=64, choices=TherapyRole.choices, default=TherapyRole.OTHER)
    patient_context = models.TextField(blank=True)
    histology_context = models.CharField(max_length=255, blank=True)
    stage_context = models.CharField(max_length=255, blank=True)
    recommendation_strength = models.CharField(max_length=100, blank=True)
    evidence_level = models.CharField(max_length=100, blank=True)
    special_notes = models.TextField(blank=True)
    source_section = models.ForeignKey(
        GuidelineSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="therapy_rules",
    )

    class Meta:
        ordering = ["therapy_definition__name"]
        indexes = [
            models.Index(fields=["biomarker_variant_rule", "therapy_line"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "guideline_document",
                    "biomarker_variant_rule",
                    "therapy_definition",
                    "therapy_line",
                    "source_section",
                ],
                name="unique_guideline_therapy_rule",
            ),
        ]

    def __str__(self):
        return f"{self.biomarker_variant_rule} -> {self.therapy_definition}"


class StrategyReport(TimeStampedModel):
    your_panel = models.ForeignKey(Panel, on_delete=models.CASCADE, related_name="strategy_reports_as_yours")
    competitor_panel = models.ForeignKey(
        Panel,
        on_delete=models.CASCADE,
        related_name="strategy_reports_as_competitor",
    )
    guideline_document = models.ForeignKey(
        GuidelineDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="strategy_reports",
    )
    market_account = models.ForeignKey(
        MarketAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="strategy_reports",
    )
    title = models.CharField(max_length=255, blank=True)
    disease_focus = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=64, default="draft")
    executive_summary = models.TextField(blank=True)
    swot_json = models.JSONField(default=dict, blank=True)
    market_gap_json = models.JSONField(default=dict, blank=True)
    guideline_advantages_json = models.JSONField(default=dict, blank=True)
    campaigns_json = models.JSONField(default=list, blank=True)
    sales_pitch_text = models.TextField(blank=True)
    llm_provider = models.CharField(max_length=100, blank=True)
    llm_model = models.CharField(max_length=100, blank=True)
    report_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Strategy: {self.your_panel.name} vs {self.competitor_panel.name}"


class LLMGenerationLog(TimeStampedModel):
    marketing_plan = models.ForeignKey(
        MarketingPlan,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="llm_logs",
    )
    strategy_report = models.ForeignKey(
        StrategyReport,
        on_delete=models.CASCADE,
        related_name="llm_logs",
        null=True,
        blank=True,
    )
    provider = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    operation = models.CharField(max_length=100, default="strategy_generation")
    status = models.CharField(max_length=64, default="completed")
    prompt_text = models.TextField(blank=True)
    response_text = models.TextField(blank=True)
    response_json = models.JSONField(default=dict, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    response_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider}:{self.model_name} - {self.operation}"


class PanelGuidelineMatch(TimeStampedModel):
    panel = models.ForeignKey(Panel, on_delete=models.CASCADE, related_name="guideline_matches")
    guideline_document = models.ForeignKey(
        GuidelineDocument,
        on_delete=models.CASCADE,
        related_name="panel_matches",
    )
    cancer_type = models.CharField(max_length=255)
    match_status = models.CharField(max_length=100, blank=True)
    matched_genes_count = models.PositiveIntegerField(default=0)
    missing_actionable_genes_count = models.PositiveIntegerField(default=0)
    coverage_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    summary_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["panel", "guideline_document"],
                name="unique_panel_guideline_match",
            ),
        ]

    def __str__(self):
        return f"{self.panel.name} vs {self.guideline_document.name}"


class PanelGuidelineGeneMatch(TimeStampedModel):
    panel_guideline_match = models.ForeignKey(
        PanelGuidelineMatch,
        on_delete=models.CASCADE,
        related_name="gene_matches",
    )
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE, related_name="guideline_gene_matches")
    biomarker_definition = models.ForeignKey(
        BiomarkerDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_gene_matches",
    )
    match_type = models.CharField(max_length=64, choices=MatchType.choices)
    testing_relevance = models.TextField(blank=True)
    therapy_relevance = models.TextField(blank=True)
    notes_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["gene__symbol"]
        constraints = [
            models.UniqueConstraint(
                fields=["panel_guideline_match", "gene", "match_type"],
                name="unique_panel_guideline_gene_match",
            ),
        ]

    def __str__(self):
        return f"{self.panel_guideline_match} - {self.gene.symbol}"
