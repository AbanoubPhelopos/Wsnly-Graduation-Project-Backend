from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RouteHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "source_type",
                    models.CharField(
                        choices=[("text", "Text"), ("map", "Map")], max_length=10
                    ),
                ),
                ("input_text", models.TextField(blank=True, null=True)),
                (
                    "origin_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "destination_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("origin_lat", models.FloatField(blank=True, null=True)),
                ("origin_lon", models.FloatField(blank=True, null=True)),
                ("destination_lat", models.FloatField(blank=True, null=True)),
                ("destination_lon", models.FloatField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("success", "Success"), ("failed", "Failed")],
                        max_length=20,
                    ),
                ),
                ("error_code", models.CharField(blank=True, max_length=64, null=True)),
                ("error_message", models.TextField(blank=True, null=True)),
                ("total_distance_meters", models.FloatField(blank=True, null=True)),
                ("total_duration_seconds", models.FloatField(blank=True, null=True)),
                ("step_count", models.IntegerField(blank=True, null=True)),
                ("ai_latency_ms", models.FloatField(blank=True, null=True)),
                ("routing_latency_ms", models.FloatField(blank=True, null=True)),
                ("total_latency_ms", models.FloatField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="route_history",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="routehistory",
            index=models.Index(
                fields=["source_type", "created_at"],
                name="history_rou_source__cc7f59_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="routehistory",
            index=models.Index(
                fields=["status", "created_at"], name="history_rou_status_93f076_idx"
            ),
        ),
    ]
