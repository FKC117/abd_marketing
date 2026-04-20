from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import GuidelineUploadForm, SignInForm, SignUpForm
from .models import GuidelineDocument


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
            messages.success(
                request,
                f"{guideline.name} was uploaded and marked as imported. Next we can connect the extraction run to this workflow.",
            )
            return redirect("medstratix:guideline_workspace")
    else:
        form = GuidelineUploadForm()

    context = {
        "page_title": "Guideline Workspace",
        "form": form,
        "guidelines": GuidelineDocument.objects.order_by("-created_at")[:12],
    }
    return render(request, "medstratix/guideline_workspace.html", context)
