from django.urls import path
from . import views

urlpatterns = [
    path("_health", views.health, name="health"),
    path("templates/import/", views.import_template_docx, name="import_template_docx"),
]
