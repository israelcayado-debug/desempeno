from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("evaluations", "0006_evaluationitem_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="evaluationperiod",
            name="closed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
