from django.urls import path

from .views import (
    SignInView,
    SignOutView,
    SignUpView,
    guideline_dashboard,
    guideline_detail,
    guideline_workspace,
    home,
    run_guideline_extraction,
    run_guideline_structuring,
    therapy_panels,
    testing_panels,
)

app_name = "medstratix"

urlpatterns = [
    path("", home, name="home"),
    path("workspace/dashboard/", guideline_dashboard, name="guideline_dashboard"),
    path("workspace/testing-panels/", testing_panels, name="testing_panels"),
    path("workspace/therapy-panels/", therapy_panels, name="therapy_panels"),
    path("workspace/", guideline_workspace, name="guideline_workspace"),
    path("workspace/<int:pk>/", guideline_detail, name="guideline_detail"),
    path("workspace/<int:pk>/run/", run_guideline_extraction, name="run_guideline_extraction"),
    path("workspace/<int:pk>/structure/", run_guideline_structuring, name="run_guideline_structuring"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("signin/", SignInView.as_view(), name="signin"),
    path("logout/", SignOutView.as_view(), name="logout"),
]
