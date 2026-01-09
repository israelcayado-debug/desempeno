from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.org.models import Employee
from apps.templates_eval.models import TemplateQuestion


class EvaluationPeriod(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_closed", "start_date", "end_date"]),
        ]

    def __str__(self) -> str:
        return self.name


class Evaluation(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        FINAL = "FINAL", "Final"

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="evaluations")
    evaluator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="evaluations_made")
    period = models.ForeignKey(EvaluationPeriod, on_delete=models.PROTECT, related_name="evaluations")
    template=models.ForeignKey(
        "templates_eval.EvaluationTemplate",
       on_delete=models.PROTECT,
       related_name="evaluations",
       null=True,
       blank=True,
       )
  

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    reopened_at = models.DateTimeField(null=True, blank=True)
    reopen_reason = models.TextField(null=True, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)

    frozen_position_code = models.CharField(max_length=8)
    frozen_position_name = models.CharField(max_length=160)
    evaluator_comment = models.TextField(blank=True, default="")
    overall_comment = models.TextField(blank=True, default="")

    final_score = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)

    class Meta:
        unique_together = [("employee", "period")]
        indexes = [
            models.Index(fields=["period", "status"]),
            models.Index(fields=["evaluator", "period"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} - {self.period}"

    def set_status(self, new_status: str, *, reason: str | None = None) -> None:
        if new_status == self.status:
            return

        now = timezone.now()

        if new_status == self.Status.SUBMITTED:
            self.submitted_at = self.submitted_at or now
        elif new_status == self.Status.FINAL:
            self.finalized_at = self.finalized_at or now
        elif new_status == self.Status.DRAFT:
            self.reopened_at = now
            if reason:
                self.reopen_reason = reason

        self.status = new_status
        self.status_changed_at = now


class EvaluationItem(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="items",
    )
    section_title = models.CharField(max_length=255)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20)
    is_required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField()
    value_scale = models.PositiveSmallIntegerField(null=True, blank=True)
    value_yes_no = models.BooleanField(null=True, blank=True)
    value_text = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["display_order"]


class EvaluationScore(TimeStampedModel):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="scores")
    template_item = models.ForeignKey(TemplateQuestion, on_delete=models.PROTECT)
    score = models.PositiveSmallIntegerField()  # 1..5
    comment = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [("evaluation", "template_item")]
class EvaluationAnswer(TimeStampedModel):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        "templates_eval.TemplateQuestion",
        on_delete=models.PROTECT,
        related_name="answers",
    )

    # Respuestas posibles según tipo de pregunta
    score = models.PositiveSmallIntegerField(null=True, blank=True)   # SCALE_1_5
    yes_no = models.BooleanField(null=True, blank=True)              # YES_NO
    text = models.TextField(blank=True)                              # TEXT

    class Meta:
        unique_together = [("evaluation", "question")]
        indexes = [
            models.Index(fields=["evaluation", "question"]),
        ]

    def __str__(self) -> str:
        return f"{self.evaluation_id} - {self.question_id}"


class EvaluationBlockComment(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="block_comments",
    )
    block_code = models.CharField(max_length=10)
    comment = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["evaluation", "block_code"],
                name="uniq_eval_block_comment",
            )
        ]

    def __str__(self) -> str:
        return f"{self.evaluation_id} - {self.block_code}"


class ReportFilterPreset(TimeStampedModel):
    name = models.CharField(max_length=120)
    scope = models.CharField(max_length=80, db_index=True)
    query_params = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="report_filter_presets"
    )
    is_shared = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["scope", "created_by"]),
        ]

    def __str__(self) -> str:
        return f"{self.scope}: {self.name}"
