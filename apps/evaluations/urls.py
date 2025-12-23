from django.urls import path
from . import views

urlpatterns = [
    path("my-team/", views.my_team, name="my_team"),
    path("evaluate/<int:employee_id>/", views.evaluate_employee, name="evaluate_employee"),
]
