from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0020_color_config_use_feature_props"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chart",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="colorconfig",
            name="single_color",
            field=models.CharField(blank=True, default="", max_length=12),
        ),
        migrations.AlterField(
            model_name="dataset",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="taskresult",
            name="error",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="taskresult",
            name="status",
            field=models.TextField(blank=True, default=""),
        ),
    ]
