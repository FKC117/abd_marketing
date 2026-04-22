from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import (
    CompanyType,
    FinalMarketingReport,
    GuidelineDocument,
    GuidelineStatus,
    MarketAccount,
    MarketingPlan,
    MarketStakeholder,
    Panel,
    SampleType,
)


def apply_widget_style(fields):
    for name, field in fields.items():
        css_class = "form-control"
        if isinstance(field.widget, forms.FileInput):
            css_class = "form-control form-control-file"

        attrs = {
            "class": css_class,
        }

        if name == "username":
            attrs["placeholder"] = "Enter your username"
        elif name == "email":
            attrs["placeholder"] = "Enter your email"
        elif "password" in name:
            attrs["placeholder"] = "Enter your password"
        elif name == "name":
            attrs["placeholder"] = "Guideline name"
        elif name == "cancer_type":
            attrs["placeholder"] = "Cancer type"
        elif name == "version":
            attrs["placeholder"] = "Version"
        elif name == "year":
            attrs["placeholder"] = "Year"

        field.widget.attrs.update(attrs)


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_style(self.fields)


class SignInForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"autofocus": True}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_style(self.fields)


class GuidelineUploadForm(forms.ModelForm):
    class Meta:
        model = GuidelineDocument
        fields = ["name", "cancer_type", "version", "year", "published_at", "source_file"]
        widgets = {
            "published_at": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_style(self.fields)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.status = GuidelineStatus.IMPORTED
        if commit:
            instance.save()
        return instance


class PanelUploadForm(forms.Form):
    CURRENCY_CHOICES = (
        ("BDT", "BDT"),
        ("USD", "USD"),
        ("EUR", "EUR"),
    )

    company_name = forms.CharField(max_length=255)
    panel_name = forms.CharField(max_length=255)
    website_url = forms.URLField(required=False, label="Website address")
    gene_panel_available = forms.BooleanField(required=False, initial=True, label="Gene panel data available")
    sample_type = forms.ChoiceField(choices=SampleType.choices, initial=SampleType.TISSUE)
    supports_dna_ngs = forms.BooleanField(required=False, initial=True, label="DNA NGS")
    supports_rna_ngs = forms.BooleanField(required=False, label="RNA NGS")
    supports_fusions = forms.BooleanField(required=False, label="Fusion detection")
    supports_cnv = forms.BooleanField(required=False, label="CNV / amplification")
    supports_msi = forms.BooleanField(required=False, label="MSI support")
    supports_tmb = forms.BooleanField(required=False, label="TMB support")
    supports_ihc = forms.BooleanField(required=False, label="IHC companion testing")
    supports_fish = forms.BooleanField(required=False, label="FISH companion testing")
    price = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    price_currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial="BDT", label="Price currency")
    tat = forms.CharField(max_length=100, required=False, label="Turnaround time")
    gene_text = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "placeholder": "Paste gene symbols separated by commas, spaces, or new lines",
            }
        ),
        label="Gene list",
    )
    gene_file = forms.FileField(required=False, label="CSV or text file")
    company_type = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, company_type=CompanyType.OTHER, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_type = company_type
        self.initial["company_type"] = company_type
        apply_widget_style(self.fields)
        if company_type == CompanyType.YOURS:
            self.fields["gene_panel_available"].initial = True
            self.fields["company_name"].widget.attrs["placeholder"] = "Your company name"
            self.fields["panel_name"].widget.attrs["placeholder"] = "Your panel name"
        elif company_type == CompanyType.COMPETITOR:
            self.fields["gene_panel_available"].initial = False
            self.fields["company_name"].widget.attrs["placeholder"] = "Competitor company name"
            self.fields["panel_name"].widget.attrs["placeholder"] = "Competitor panel name"
            self.fields["website_url"].widget.attrs["placeholder"] = "https://competitor-site.example/panel"
        self.fields["sample_type"].widget.attrs["class"] = "form-control"
        self.fields["price"].widget.attrs["placeholder"] = "Price"
        self.fields["tat"].widget.attrs["placeholder"] = "e.g. 10 business days"
        capability_fields = (
            "supports_dna_ngs",
            "supports_rna_ngs",
            "supports_fusions",
            "supports_cnv",
            "supports_msi",
            "supports_tmb",
            "supports_ihc",
            "supports_fish",
        )
        for field_name in capability_fields:
            self.fields[field_name].widget.attrs["class"] = "checkbox-input"
        self.fields["gene_panel_available"].widget.attrs["class"] = "checkbox-input"

    def clean_company_type(self):
        value = self.cleaned_data["company_type"]
        return value or self.company_type

    def clean(self):
        cleaned_data = super().clean()
        gene_text = (cleaned_data.get("gene_text") or "").strip()
        gene_file = cleaned_data.get("gene_file")
        gene_panel_available = cleaned_data.get("gene_panel_available", False)
        company_type = cleaned_data.get("company_type") or self.company_type

        if company_type == CompanyType.COMPETITOR and not gene_text and not gene_file:
            cleaned_data["gene_panel_available"] = False
            return cleaned_data

        if gene_panel_available and not gene_text and not gene_file:
            raise forms.ValidationError("If gene panel data is available, provide a gene list in the text area or upload a CSV/text file.")
        return cleaned_data


class PanelComparisonSelectForm(forms.Form):
    your_panels = forms.ModelMultipleChoiceField(
        queryset=Panel.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    competitor_panels = forms.ModelMultipleChoiceField(
        queryset=Panel.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["your_panels"].queryset = Panel.objects.filter(company__type=CompanyType.YOURS).select_related("company")
        self.fields["competitor_panels"].queryset = Panel.objects.filter(company__type=CompanyType.COMPETITOR).select_related("company")


class MarketAccountForm(forms.ModelForm):
    class Meta:
        model = MarketAccount
        fields = [
            "name",
            "institution_type",
            "city",
            "decision_style",
            "disease_focus",
            "estimated_test_volume",
            "evidence_sensitivity",
            "price_sensitivity",
            "tat_sensitivity",
            "conference_interest",
            "education_interest",
            "market_corruption_pressure",
            "referral_distortion_risk",
            "compliance_red_flags",
            "ethical_growth_goal",
            "notes",
        ]
        widgets = {
            "compliance_red_flags": forms.Textarea(attrs={"rows": 4}),
            "ethical_growth_goal": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_style(self.fields)


class MarketStakeholderForm(forms.ModelForm):
    class Meta:
        model = MarketStakeholder
        fields = [
            "account",
            "name",
            "is_verified",
            "role",
            "specialty",
            "influence_level",
            "evidence_preference",
            "conference_interest",
            "service_expectation",
            "behavioral_notes",
        ]
        widgets = {
            "service_expectation": forms.Textarea(attrs={"rows": 4}),
            "behavioral_notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_style(self.fields)


class MarketingPlanBuilderForm(forms.Form):
    OUTPUT_STYLE_CHOICES = (
        ("brief_plan", "Brief Marketing Plan"),
        ("detailed_plan", "Detailed Marketing Plan"),
        ("launch_plan", "90-Day Launch Plan"),
        ("growth_plan", "Growth Plan"),
        ("account_plan", "Account Plan"),
    )

    title = forms.CharField(max_length=255)
    objective = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    geography = forms.CharField(required=False, max_length=255)
    disease_focus = forms.CharField(required=False, max_length=255)
    output_style = forms.ChoiceField(choices=OUTPUT_STYLE_CHOICES, initial="brief_plan")
    include_product_context = forms.BooleanField(required=False, initial=False)
    strategy_model = forms.ChoiceField(choices=(), required=False)
    planning_horizon = forms.CharField(required=False, max_length=255)
    expected_monthly_samples = forms.IntegerField(required=False, min_value=0)
    expected_quarterly_revenue_bdt = forms.DecimalField(required=False, max_digits=14, decimal_places=2)
    expected_year_one_revenue_bdt = forms.DecimalField(required=False, max_digits=14, decimal_places=2)
    revenue_guardrail_note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    strategist_note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 6}))
    source_plans = forms.ModelMultipleChoiceField(
        queryset=MarketingPlan.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    market_accounts = forms.ModelMultipleChoiceField(
        queryset=MarketAccount.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    your_panels = forms.ModelMultipleChoiceField(
        queryset=Panel.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    competitor_panels = forms.ModelMultipleChoiceField(
        queryset=Panel.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, model_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source_plans"].queryset = MarketingPlan.objects.order_by("-created_at")
        self.fields["market_accounts"].queryset = MarketAccount.objects.order_by("name")
        self.fields["your_panels"].queryset = Panel.objects.filter(company__type=CompanyType.YOURS).select_related("company")
        self.fields["competitor_panels"].queryset = Panel.objects.filter(company__type=CompanyType.COMPETITOR).select_related("company")
        self.fields["strategy_model"].choices = model_choices or ()
        apply_widget_style(
            {
                "title": self.fields["title"],
                "objective": self.fields["objective"],
                "geography": self.fields["geography"],
                "disease_focus": self.fields["disease_focus"],
                "output_style": self.fields["output_style"],
                "strategy_model": self.fields["strategy_model"],
                "planning_horizon": self.fields["planning_horizon"],
                "expected_monthly_samples": self.fields["expected_monthly_samples"],
                "expected_quarterly_revenue_bdt": self.fields["expected_quarterly_revenue_bdt"],
                "expected_year_one_revenue_bdt": self.fields["expected_year_one_revenue_bdt"],
                "revenue_guardrail_note": self.fields["revenue_guardrail_note"],
                "strategist_note": self.fields["strategist_note"],
            }
        )


class MarketingPlanSectionEditForm(forms.Form):
    executive_summary_override = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    market_research_override = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 5}))
    swot_override = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 5}))
    personas_override = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 5}))
    uvp_override = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    campaigns_override = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 5}))
    sales_pitch_override = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    next_steps_override = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_style(
            {
                "executive_summary_override": self.fields["executive_summary_override"],
                "market_research_override": self.fields["market_research_override"],
                "swot_override": self.fields["swot_override"],
                "personas_override": self.fields["personas_override"],
                "uvp_override": self.fields["uvp_override"],
                "campaigns_override": self.fields["campaigns_override"],
                "sales_pitch_override": self.fields["sales_pitch_override"],
                "next_steps_override": self.fields["next_steps_override"],
            }
        )


class FinalMarketingReportBuilderForm(forms.Form):
    CHRONOLOGY_CHOICES = (
        ("oldest_first", "Oldest to Newest"),
        ("newest_first", "Newest to Oldest"),
        ("plan_ladder", "Plan Ladder (Brief to Account)"),
        ("custom_ids", "Custom ID Order"),
    )

    title = forms.CharField(max_length=255)
    selected_plans = forms.ModelMultipleChoiceField(
        queryset=MarketingPlan.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    chronology_mode = forms.ChoiceField(choices=CHRONOLOGY_CHOICES, initial="oldest_first")
    custom_plan_order = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Use comma-separated plan IDs when Custom ID Order is selected. Example: 10,12,15",
    )
    strategist_note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 5}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["selected_plans"].queryset = MarketingPlan.objects.order_by("-created_at")
        apply_widget_style(
            {
                "title": self.fields["title"],
                "chronology_mode": self.fields["chronology_mode"],
                "custom_plan_order": self.fields["custom_plan_order"],
                "strategist_note": self.fields["strategist_note"],
            }
        )

    def clean_custom_plan_order(self):
        raw = (self.cleaned_data.get("custom_plan_order") or "").strip()
        if not raw:
            return []
        values = []
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                values.append(int(token))
            except ValueError as exc:
                raise forms.ValidationError("Custom order must contain only comma-separated numeric plan IDs.") from exc
        return values

    def clean(self):
        cleaned_data = super().clean()
        selected_plans = list(cleaned_data.get("selected_plans") or [])
        chronology_mode = cleaned_data.get("chronology_mode")
        custom_order = cleaned_data.get("custom_plan_order") or []
        selected_ids = {plan.pk for plan in selected_plans}

        if chronology_mode == "custom_ids":
            if not custom_order:
                raise forms.ValidationError("Provide custom plan IDs when using Custom ID Order.")
            if set(custom_order) != selected_ids:
                raise forms.ValidationError("Custom ID Order must contain exactly the same selected plan IDs.")
        return cleaned_data
