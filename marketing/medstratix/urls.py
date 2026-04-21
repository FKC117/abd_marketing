from django.urls import path

from .views import (
    SignInView,
    SignOutView,
    SignUpView,
    biomarker_catalog,
    guideline_dashboard,
    guideline_detail,
    guideline_workspace,
    home,
    market_workspace,
    panel_compare_result,
    panel_compare_setup,
    panel_edit,
    panel_workspace,
    run_guideline_extraction,
    run_guideline_structuring,
    strategy_detail,
    strategy_workspace,
    therapy_panels,
    testing_panels,
)

app_name = "medstratix"

urlpatterns = [
    path("", home, name="home"),
    path("workspace/panels/", panel_workspace, name="panel_workspace"),
    path("workspace/panels/compare/", panel_compare_setup, name="panel_compare_setup"),
    path("workspace/panels/compare/result/", panel_compare_result, name="panel_compare_result"),
    path("workspace/market/", market_workspace, name="market_workspace"),
    path("workspace/strategies/", strategy_workspace, name="strategy_workspace"),
    path("workspace/strategies/<int:pk>/", strategy_detail, name="strategy_detail"),
    path("workspace/panels/<int:pk>/edit/", panel_edit, name="panel_edit"),
    path("workspace/dashboard/", guideline_dashboard, name="guideline_dashboard"),
    path("workspace/biomarkers/", biomarker_catalog, name="biomarker_catalog"),
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
