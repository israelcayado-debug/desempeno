from django.urls import path
from . import views

urlpatterns = [
    path("my-team/", views.my_team, name="my_team"),
    path("evaluate/<int:employee_id>/<int:period_id>/", views.evaluate_employee, name="evaluate_employee"),
    path("reports/period/", views.report_period, name="report_period"),
    path("reports/period/<int:period_id>/", views.report_period, name="report_period_detail"),
    path("reports/period/<int:period_id>/export.csv", views.report_period_export_csv, name="report_period_export_csv"),
    path("reports/period/<int:period_id>/export_items.csv", views.report_period_export_items_csv, name="report_period_export_items_csv"),
    path("reports/period/<int:period_id>/export.xlsx", views.report_period_export_xlsx, name="report_period_export_xlsx"),
    path("reports/system/", views.report_system, name="report_system"),
]
