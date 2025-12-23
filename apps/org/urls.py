from django.urls import path
from . import views

urlpatterns = [
    path("_health", views.health, name="health"),
]
