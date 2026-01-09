from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("templates_eval", "0001_initial"),
        ("evaluations", "0009_evaluation_comments"),
    ]

    operations = [
        migrations.AlterField(
            model_name="evaluationscore",
            name="template_item",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="templates_eval.templatequestion",
            ),
        ),
    ]
