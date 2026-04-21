from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import (
    CompanyType,
    GuidelineDocument,
    GuidelineStatus,
    MarketAccount,
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
            self.fields["company_name"].widget.attrs["placeholder"] = "Your company name"
            self.fields["panel_name"].widget.attrs["placeholder"] = "Your panel name"
        elif company_type == CompanyType.COMPETITOR:
            self.fields["company_name"].widget.attrs["placeholder"] = "Competitor company name"
            self.fields["panel_name"].widget.attrs["placeholder"] = "Competitor panel name"
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

    def clean_company_type(self):
        value = self.cleaned_data["company_type"]
        return value or self.company_type

    def clean(self):
        cleaned_data = super().clean()
        gene_text = (cleaned_data.get("gene_text") or "").strip()
        gene_file = cleaned_data.get("gene_file")
        if not gene_text and not gene_file:
            raise forms.ValidationError("Provide a gene list in the text area or upload a CSV/text file.")
        return cleaned_data


class PanelComparisonSelectForm(forms.Form):
    your_panel = forms.ModelChoiceField(queryset=Panel.objects.none(), empty_label="Select your panel")
    competitor_panels = forms.ModelMultipleChoiceField(
        queryset=Panel.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["your_panel"].queryset = Panel.objects.filter(company__type=CompanyType.YOURS).select_related("company")
        self.fields["competitor_panels"].queryset = Panel.objects.filter(company__type=CompanyType.COMPETITOR).select_related("company")
        apply_widget_style({"your_panel": self.fields["your_panel"]})


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
