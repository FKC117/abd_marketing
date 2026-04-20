from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import GuidelineDocument, GuidelineStatus


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
