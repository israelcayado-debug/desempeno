from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel


class Department(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)

    def __str__(self) -> str:
        return self.name


class Position(TimeStampedModel):
    code = models.CharField(max_length=8, unique=True)  # P00..P35
    name = models.CharField(max_length=160)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    professional_group = models.CharField(max_length=32)  # GP1..GP6
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["department", "professional_group"])]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Employee(TimeStampedModel):
    dni = models.CharField(max_length=16, unique=True)
    full_name = models.CharField(max_length=200, db_index=True)
    hire_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    prl_position_label = models.CharField(max_length=200, blank=True, default="")

    evaluation_position = models.ForeignKey(
        Position, on_delete=models.PROTECT, null=True, blank=True, related_name="employees"
    )

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="team"
    )

    class Meta:
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["manager", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.dni})"
