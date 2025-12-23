from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.org.urls")),
    path("", include("apps.evaluations.urls")),
    path("", include("apps.reporting.urls")),
    path("", include("apps.imports.urls")),
]
