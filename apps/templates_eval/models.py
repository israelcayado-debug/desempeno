from django.db import models
from django.utils import timezone



class EvaluationTemplate(models.Model):
    name = models.CharField(max_length=200)
    base_code = models.CharField(max_length=20, blank=True, default="")
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    source_hash = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        unique_together = ("name", "version")
        constraints = [
            models.UniqueConstraint(fields=["base_code", "version"], name="uniq_template_base_version"),
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"


class TemplateAssignment(models.Model):
    template = models.ForeignKey(EvaluationTemplate, on_delete=models.PROTECT, related_name="assignments")
    position = models.ForeignKey("org.Position", on_delete=models.PROTECT, related_name="template_assignments")
    is_default = models.BooleanField(default=True)

    class Meta:
        unique_together = ("template", "position")

    def __str__(self):
        return f"{self.position} -> {self.template}"


class TemplateSection(models.Model):
    template = models.ForeignKey(EvaluationTemplate, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.template}: {self.title}"


class TemplateQuestion(models.Model):
    SCALE_1_5 = "SCALE_1_5"
    YES_NO = "YES_NO"
    TEXT = "TEXT"

    QUESTION_TYPES = [
        (SCALE_1_5, "Escala 1-5"),
        (YES_NO, "Sí/No"),
        (TEXT, "Texto"),
    ]

    section = models.ForeignKey(TemplateSection, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=500)
    help_text = models.CharField(max_length=500, blank=True)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default=SCALE_1_5)
    required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=1)
# Question model
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text
from django.db import models


class TemplateItem(models.Model):
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class TemplateActive(models.Model):
    base_code = models.CharField(max_length=20, unique=True)
    template = models.ForeignKey(
        "templates_eval.EvaluationTemplate",
        on_delete=models.PROTECT,
        related_name="active_for",
    )

    def __str__(self):
        return f"{self.base_code} -> {self.template.code}"
