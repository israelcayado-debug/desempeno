from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("evaluations", "0008_reportfilterpreset"),
    ]

    operations = [
        migrations.AddField(
            model_name="evaluation",
            name="overall_comment",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.CreateModel(
            name="EvaluationBlockComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("block_code", models.CharField(max_length=10)),
                ("comment", models.TextField(blank=True, default="")),
                (
                    "evaluation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="block_comments",
                        to="evaluations.evaluation",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="evaluationblockcomment",
            constraint=models.UniqueConstraint(
                fields=("evaluation", "block_code"),
                name="uniq_eval_block_comment",
            ),
        ),
    ]
