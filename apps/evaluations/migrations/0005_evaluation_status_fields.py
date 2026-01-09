from django.db import migrations, models


def migrate_statuses(apps, schema_editor):
    Evaluation = apps.get_model("evaluations", "Evaluation")
    Evaluation.objects.filter(status="CLOSED").update(status="FINAL")


class Migration(migrations.Migration):
    dependencies = [
        ("evaluations", "0004_evaluation_evaluator_comment"),
    ]

    operations = [
        migrations.AddField(
            model_name="evaluation",
            name="submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="evaluation",
            name="finalized_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="evaluation",
            name="reopened_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="evaluation",
            name="reopen_reason",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="evaluation",
            name="status_changed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="status",
            field=models.CharField(
                choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("FINAL", "Final")],
                db_index=True,
                default="DRAFT",
                max_length=12,
            ),
        ),
        migrations.RunPython(migrate_statuses, migrations.RunPython.noop),
    ]
