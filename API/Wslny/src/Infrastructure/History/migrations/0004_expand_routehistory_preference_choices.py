from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("history", "0003_backfill_has_result_for_existing_rows"),
    ]

    operations = [
        migrations.AlterField(
            model_name="routehistory",
            name="preference",
            field=models.CharField(
                choices=[
                    ("optimal", "Optimal"),
                    ("fastest", "Fastest"),
                    ("cheapest", "Cheapest"),
                    ("bus_only", "Bus Only"),
                    ("microbus_only", "Microbus Only"),
                    ("metro_only", "Metro Only"),
                ],
                default="optimal",
                max_length=20,
            ),
        ),
    ]
