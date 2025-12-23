from django.contrib import admin
from .models import Department, Position, Employee

# NUEVO
from apps.core.permissions import can_manage_employees


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name",)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "professional_group", "is_active")
    list_filter = ("department", "professional_group", "is_active")
    search_fields = ("code", "name")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "dni",
        "is_active",
        "evaluation_position",
        "manager",
    )
    list_filter = ("is_active", "evaluation_position")
    search_fields = ("full_name", "dni")

    # NUEVO
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("evaluation_position", "manager")
        if can_manage_employees(request.user):
            return qs
        return qs.filter(manager=request.user, is_active=True)
