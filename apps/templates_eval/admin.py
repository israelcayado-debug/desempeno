from django.contrib import admin
from .models import EvaluationTemplate, TemplateAssignment, TemplateSection, TemplateQuestion


class TemplateQuestionInline(admin.TabularInline):
    model = TemplateQuestion
    extra = 0


@admin.register(TemplateSection)
class TemplateSectionAdmin(admin.ModelAdmin):
    list_display = ("template", "title", "order")
    inlines = [TemplateQuestionInline]


@admin.register(EvaluationTemplate)
class EvaluationTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(TemplateAssignment)
class TemplateAssignmentAdmin(admin.ModelAdmin):
    list_display = ("position", "template", "is_default")
    list_filter = ("is_default", "position")
    search_fields = ("position__name", "template__name")

