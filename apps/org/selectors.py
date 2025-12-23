from django.db.models import QuerySet
from apps.org.models import Employee
from apps.core.permissions import can_manage_employees

def employees_visible_to(user) -> QuerySet[Employee]:
    qs = Employee.objects.all()
    if can_manage_employees(user):
        return qs
    return qs.filter(manager=user, is_active=True)
