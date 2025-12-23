from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from apps.core.permissions import can_evaluate
from apps.org.selectors import employees_visible_to


@login_required
def my_team(request):
    if not can_evaluate(request.user):
        raise PermissionDenied

    employees = (
        employees_visible_to(request.user)
        .select_related("evaluation_position", "manager")
        .order_by("full_name")
    )

    return render(request, "evaluations/my_team.html", {"employees": employees})

@login_required
def evaluate_employee(request, employee_id: int):
    if not can_evaluate(request.user):
        raise PermissionDenied

    # En esta fase solo mostramos la ficha del empleado y confirmamos acceso.
    # En el siguiente paso lo conectamos con periodo + plantilla + formulario.
    employee = employees_visible_to(request.user).filter(id=employee_id).select_related("evaluation_position").first()
    if not employee:
        raise PermissionDenied

    return render(request, "evaluations/evaluate_employee.html", {"employee": employee})

