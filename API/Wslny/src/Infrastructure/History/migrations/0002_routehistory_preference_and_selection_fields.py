from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("history", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="routehistory",
            name="estimated_fare",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="routehistory",
            name="has_result",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="routehistory",
            name="preference",
            field=models.CharField(
                choices=[
                    ("optimal", "Optimal"),
                    ("fastest", "Fastest"),
                    ("cheapest", "Cheapest"),
                ],
                default="optimal",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="routehistory",
            name="request_id",
            field=models.CharField(blank=True, db_index=True, max_length=36, null=True),
        ),
        migrations.AddField(
            model_name="routehistory",
            name="selected_route_type",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="routehistory",
            name="unresolved_reason",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="routehistory",
            name="walk_distance_meters",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
