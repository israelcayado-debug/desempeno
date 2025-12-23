from django.db import models
from apps.core.models import TimeStampedModel
from apps.org.models import Position


class Template(TimeStampedModel):
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name="templates")
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    source_docx_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = [("position", "version")]
        indexes = [models.Index(fields=["position", "is_active"])]

    def __str__(self) -> str:
        return f"{self.position.code} v{self.version}"


class TemplateBlock(TimeStampedModel):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name="blocks")
    key = models.CharField(max_length=4)  # A, B, C...
    name = models.CharField(max_length=200)
    weight_percent = models.DecimalField(max_digits=6, decimal_places=2)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [("template", "key")]
        ordering = ["order"]


class TemplateItem(TimeStampedModel):
    block = models.ForeignKey(TemplateBlock, on_delete=models.CASCADE, related_name="items")
    subcriterion = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=1)
    item_weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["order"]
