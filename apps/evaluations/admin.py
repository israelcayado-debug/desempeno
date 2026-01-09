from django.contrib import admin
from .models import EvaluationPeriod, Evaluation, EvaluationScore


@admin.register(EvaluationPeriod)
class EvaluationPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_closed")
    list_filter = ("is_closed",)
    search_fields = ("name",)
    ordering = ("-start_date",)


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "period",
        "evaluator",
        "status",
        "final_score",
        "created_at",
    )
    list_filter = ("status", "period")
    search_fields = (
        "employee__full_name",
        "employee__dni",
        "evaluator__username",
    )


@admin.register(EvaluationScore)
class EvaluationScoreAdmin(admin.ModelAdmin):
    list_display = ("evaluation", "template_item", "score", "created_at")
    search_fields = (
        "evaluation__employee__full_name",
        "evaluation__employee__dni",
    )

