from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

from config.views import home

urlpatterns = [
    path("", home, name="home"),

    path("admin/", admin.site.urls),

    # Auth
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("", include("apps.org.urls")),
    path("", include("apps.evaluations.urls")),
    path("", include("apps.reporting.urls")),
    path("", include("apps.imports.urls")),
    path("", include("apps.templates_eval.urls")),

    # Redirección "bonita" para evitar 404 en /reports/
    path("reports/", RedirectView.as_view(pattern_name="report_period", permanent=False)),
]
