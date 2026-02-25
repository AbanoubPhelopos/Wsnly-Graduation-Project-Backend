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

    PREFERENCE_OPTIMAL = "optimal"
    PREFERENCE_FASTEST = "fastest"
    PREFERENCE_CHEAPEST = "cheapest"
    PREFERENCE_BUS_ONLY = "bus_only"
    PREFERENCE_MICROBUS_ONLY = "microbus_only"
    PREFERENCE_METRO_ONLY = "metro_only"
    PREFERENCE_CHOICES = (
        (PREFERENCE_OPTIMAL, "Optimal"),
        (PREFERENCE_FASTEST, "Fastest"),
        (PREFERENCE_CHEAPEST, "Cheapest"),
        (PREFERENCE_BUS_ONLY, "Bus Only"),
        (PREFERENCE_MICROBUS_ONLY, "Microbus Only"),
        (PREFERENCE_METRO_ONLY, "Metro Only"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="route_history",
    )
    source_type = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    request_id = models.CharField(max_length=36, db_index=True, blank=True, null=True)
    input_text = models.TextField(blank=True, null=True)
    preference = models.CharField(
        max_length=20,
        choices=PREFERENCE_CHOICES,
        default=PREFERENCE_OPTIMAL,
    )
    selected_route_type = models.CharField(max_length=32, blank=True, null=True)

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
    estimated_fare = models.FloatField(blank=True, null=True)
    walk_distance_meters = models.FloatField(blank=True, null=True)
    has_result = models.BooleanField(default=False)
    unresolved_reason = models.CharField(max_length=64, blank=True, null=True)

    ai_latency_ms = models.FloatField(blank=True, null=True)
    routing_latency_ms = models.FloatField(blank=True, null=True)
    total_latency_ms = models.FloatField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["source_type", "created_at"],
                name="history_rou_source__cc7f59_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="history_rou_status_93f076_idx",
            ),
        ]
