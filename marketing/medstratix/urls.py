from django.urls import path

from .views import SignInView, SignOutView, SignUpView, guideline_workspace, home

app_name = "medstratix"

urlpatterns = [
    path("", home, name="home"),
    path("workspace/", guideline_workspace, name="guideline_workspace"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("signin/", SignInView.as_view(), name="signin"),
    path("logout/", SignOutView.as_view(), name="logout"),
]
