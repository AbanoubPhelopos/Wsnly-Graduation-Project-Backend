from django.conf import settings
from django.db import models


class RouteHistory(models.Model):
    SOURCE_TEXT = "text"
    SOURCE_MAP = "map"
    SOURCE_CHOICES = (
        (SOURCE_TEXT, "Text"),
        (SOURCE_MAP, "Map"),
    )

    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="route_history",
    )
    source_type = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    input_text = models.TextField(blank=True, null=True)

    origin_name = models.CharField(max_length=255, blank=True, null=True)
    destination_name = models.CharField(max_length=255, blank=True, null=True)
    origin_lat = models.FloatField(blank=True, null=True)
    origin_lon = models.FloatField(blank=True, null=True)
    destination_lat = models.FloatField(blank=True, null=True)
    destination_lon = models.FloatField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_code = models.CharField(max_length=64, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    total_distance_meters = models.FloatField(blank=True, null=True)
    total_duration_seconds = models.FloatField(blank=True, null=True)
    step_count = models.IntegerField(blank=True, null=True)

    ai_latency_ms = models.FloatField(blank=True, null=True)
    routing_latency_ms = models.FloatField(blank=True, null=True)
    total_latency_ms = models.FloatField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source_type", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
