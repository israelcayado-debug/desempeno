from django.db import migrations, models


def create_items_from_templates(apps, schema_editor):
    Evaluation = apps.get_model("evaluations", "Evaluation")
    EvaluationItem = apps.get_model("evaluations", "EvaluationItem")
    EvaluationAnswer = apps.get_model("evaluations", "EvaluationAnswer")
    TemplateSection = apps.get_model("templates_eval", "TemplateSection")
    TemplateQuestion = apps.get_model("templates_eval", "TemplateQuestion")

    for evaluation in Evaluation.objects.select_related("template").all().iterator():
        if not evaluation.template_id:
            continue
        if EvaluationItem.objects.filter(evaluation_id=evaluation.id).exists():
            continue

        answers = {
            a.question_id: a
            for a in EvaluationAnswer.objects.filter(evaluation_id=evaluation.id)
        }

        order = 1
        items = []
        sections = TemplateSection.objects.filter(template_id=evaluation.template_id).order_by(
            "order", "id"
        )
        for section in sections:
            questions = TemplateQuestion.objects.filter(section_id=section.id).order_by(
                "order", "id"
            )
            for q in questions:
                ans = answers.get(q.id)
                is_required = getattr(q, "is_required", None)
                if is_required is None:
                    is_required = q.required
                item = EvaluationItem(
                    evaluation_id=evaluation.id,
                    section_title=section.title,
                    question_text=q.text,
                    question_type=q.question_type,
                    is_required=bool(is_required),
                    display_order=order,
                    value_scale=getattr(ans, "score", None),
                    value_yes_no=getattr(ans, "yes_no", None),
                    value_text=getattr(ans, "text", None),
                )
                items.append(item)
                order += 1

        if items:
            EvaluationItem.objects.bulk_create(items)


class Migration(migrations.Migration):
    dependencies = [
        ("evaluations", "0005_evaluation_status_fields"),
        ("templates_eval", "0005_evaluationtemplate_base_code_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvaluationItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section_title", models.CharField(max_length=255)),
                ("question_text", models.TextField()),
                ("question_type", models.CharField(max_length=20)),
                ("is_required", models.BooleanField(default=False)),
                ("display_order", models.PositiveIntegerField()),
                ("value_scale", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("value_yes_no", models.BooleanField(blank=True, null=True)),
                ("value_text", models.TextField(blank=True, null=True)),
                (
                    "evaluation",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="items", to="evaluations.evaluation"),
                ),
            ],
            options={"ordering": ["display_order"]},
        ),
        migrations.RunPython(create_items_from_templates, migrations.RunPython.noop),
    ]
