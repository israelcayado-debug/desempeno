from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel
from apps.org.models import Employee
from apps.templates_eval.models import TemplateItem


class EvaluationPeriod(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["is_closed", "start_date", "end_date"])]

    def __str__(self) -> str:
        return self.name


class Evaluation(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        CLOSED = "CLOSED", "Closed"

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="evaluations")
    evaluator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="evaluations_made")
    period = models.ForeignKey(EvaluationPeriod, on_delete=models.PROTECT, related_name="evaluations")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    frozen_position_code = models.CharField(max_length=8)
    frozen_position_name = models.CharField(max_length=160)

    final_score = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)

    class Meta:
        unique_together = [("employee", "period")]
        indexes = [
            models.Index(fields=["period", "status"]),
            models.Index(fields=["evaluator", "period"]),
        ]


class EvaluationScore(TimeStampedModel):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="scores")
    template_item = models.ForeignKey(TemplateItem, on_delete=models.PROTECT)
    score = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [("evaluation", "template_item")]
