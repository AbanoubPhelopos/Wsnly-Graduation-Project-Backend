from django.conf import settings
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate, TruncWeek
from django.utils.dateparse import parse_date

from src.Infrastructure.History.models import RouteHistory


class RouteAnalyticsService:
    FILTER_ENUM_TO_PREFERENCE = {
        1: RouteHistory.PREFERENCE_OPTIMAL,
        2: RouteHistory.PREFERENCE_FASTEST,
        3: RouteHistory.PREFERENCE_CHEAPEST,
        4: RouteHistory.PREFERENCE_BUS_ONLY,
        5: RouteHistory.PREFERENCE_MICROBUS_ONLY,
        6: RouteHistory.PREFERENCE_METRO_ONLY,
    }
    ALLOWED_PREFERENCES = set(FILTER_ENUM_TO_PREFERENCE.values())
    DEFAULT_METRICS = [
        "requests",
        "success_rate_percent",
        "avg_total_latency_ms",
        "avg_duration_seconds",
        "avg_distance_meters",
    ]
    ALLOWED_METRICS = {
        "requests",
        "success_count",
        "failed_count",
        "success_rate_percent",
        "avg_total_latency_ms",
        "avg_ai_latency_ms",
        "avg_routing_latency_ms",
        "avg_duration_seconds",
        "avg_distance_meters",
        "avg_fare",
        "unresolved_count",
        "unresolved_rate_percent",
        "long_walk_count",
        "long_walk_rate_percent",
    }
    DEFAULT_GROUP_BY = ["day"]
    ALLOWED_GROUP_BY = {
        "day",
        "week",
        "source",
        "status",
        "filter",
        "selected_route_type",
    }
    METRIC_ANNOTATIONS = {
        "requests": lambda: Count("id"),
        "success_count": lambda: Count(
            "id", filter=Q(status=RouteHistory.STATUS_SUCCESS)
        ),
        "failed_count": lambda: Count(
            "id", filter=Q(status=RouteHistory.STATUS_FAILED)
        ),
        "avg_total_latency_ms": lambda: Avg("total_latency_ms"),
        "avg_ai_latency_ms": lambda: Avg("ai_latency_ms"),
        "avg_routing_latency_ms": lambda: Avg("routing_latency_ms"),
        "avg_duration_seconds": lambda: Avg("total_duration_seconds"),
        "avg_distance_meters": lambda: Avg("total_distance_meters"),
        "avg_fare": lambda: Avg("estimated_fare"),
        "unresolved_count": lambda: Count("id", filter=Q(has_result=False)),
        "long_walk_count": lambda: Count(
            "id",
            filter=Q(
                walk_distance_meters__isnull=False,
                walk_distance_meters__gte=settings.ROUTE_LONG_WALK_THRESHOLD_METERS,
            ),
        ),
    }
    DERIVED_METRICS = {
        "success_rate_percent",
        "unresolved_rate_percent",
        "long_walk_rate_percent",
    }
    GROUP_KEY_MAP = {
        "source": "source_type",
        "status": "status",
        "filter": "preference",
        "selected_route_type": "selected_route_type",
        "day": "day",
        "week": "week",
    }

    @staticmethod
    def _parse_csv_values(raw_value, allowed_values):
        if raw_value in (None, ""):
            return []

        parsed = []
        for token in str(raw_value).split(","):
            normalized = token.strip().lower()
            if normalized and normalized in allowed_values and normalized not in parsed:
                parsed.append(normalized)
        return parsed

    @staticmethod
    def parse_metrics(raw_metrics):
        metrics = RouteAnalyticsService._parse_csv_values(
            raw_metrics,
            RouteAnalyticsService.ALLOWED_METRICS,
        )
        return metrics or list(RouteAnalyticsService.DEFAULT_METRICS)

    @staticmethod
    def parse_group_by(raw_group_by):
        group_by = RouteAnalyticsService._parse_csv_values(
            raw_group_by,
            RouteAnalyticsService.ALLOWED_GROUP_BY,
        )
        return group_by or list(RouteAnalyticsService.DEFAULT_GROUP_BY)

    @staticmethod
    def parse_pagination(raw_limit, raw_offset):
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            limit = 50
        try:
            offset = int(raw_offset)
        except (TypeError, ValueError):
            offset = 0

        limit = min(max(limit, 1), 200)
        offset = max(offset, 0)
        return limit, offset

    @staticmethod
    def parse_sorting(raw_sort, raw_order, group_by, metrics):
        allowed_sort_fields = set(group_by) | set(metrics)
        sort_by = raw_sort if raw_sort in allowed_sort_fields else None
        order = str(raw_order or "desc").strip().lower()
        if order not in {"asc", "desc"}:
            order = "desc"

        if sort_by is None:
            if "requests" in metrics:
                return "requests", "desc"
            if metrics:
                return metrics[0], "desc"
            if group_by:
                return group_by[0], "asc"
            return "requests", "desc"

        return sort_by, order

    @staticmethod
    def _annotations_for_metrics(metrics):
        selected = set(metrics)

        if "success_rate_percent" in selected:
            selected.update({"requests", "success_count"})
        if "unresolved_rate_percent" in selected:
            selected.update({"requests", "unresolved_count"})
        if "long_walk_rate_percent" in selected:
            selected.update({"requests", "long_walk_count"})

        annotations = {}
        for metric in selected:
            builder = RouteAnalyticsService.METRIC_ANNOTATIONS.get(metric)
            if builder:
                annotations[metric] = builder()
        return annotations

    @staticmethod
    def _group_annotations(group_by):
        annotations = {}
        if "day" in group_by:
            annotations["day"] = TruncDate("created_at")
        if "week" in group_by:
            annotations["week"] = TruncWeek("created_at")
        return annotations

    @staticmethod
    def _safe_percent(numerator, denominator):
        if not denominator:
            return 0.0
        return round((numerator / denominator) * 100.0, 2)

    @staticmethod
    def _serialize_metrics(row, metrics):
        requests = row.get("requests") or 0
        success_count = row.get("success_count") or 0
        unresolved_count = row.get("unresolved_count") or 0
        long_walk_count = row.get("long_walk_count") or 0

        payload = {}
        for metric in metrics:
            if metric == "success_rate_percent":
                payload[metric] = RouteAnalyticsService._safe_percent(
                    success_count, requests
                )
            elif metric == "unresolved_rate_percent":
                payload[metric] = RouteAnalyticsService._safe_percent(
                    unresolved_count,
                    requests,
                )
            elif metric == "long_walk_rate_percent":
                payload[metric] = RouteAnalyticsService._safe_percent(
                    long_walk_count, requests
                )
            else:
                payload[metric] = row.get(metric)
        return payload

    @staticmethod
    def _serialize_group(row, group_by):
        group = {}
        for field in group_by:
            group[field] = row.get(RouteAnalyticsService.GROUP_KEY_MAP[field])
        return group

    @staticmethod
    def query_analytics(queryset, metrics, group_by):
        metric_annotations = RouteAnalyticsService._annotations_for_metrics(metrics)
        group_annotations = RouteAnalyticsService._group_annotations(group_by)
        value_keys = [RouteAnalyticsService.GROUP_KEY_MAP[field] for field in group_by]

        if value_keys:
            grouped = queryset
            if group_annotations:
                grouped = grouped.annotate(**group_annotations)
            grouped = grouped.values(*value_keys).annotate(**metric_annotations)
            rows = list(grouped)
        else:
            rows = [queryset.aggregate(**metric_annotations)]

        return [
            {
                "group": RouteAnalyticsService._serialize_group(row, group_by),
                "metrics": RouteAnalyticsService._serialize_metrics(row, metrics),
            }
            for row in rows
        ]

    @staticmethod
    def sort_rows(rows, sort_by, order):
        reverse = order == "desc"

        def sort_key(item):
            if sort_by in item["metrics"]:
                value = item["metrics"].get(sort_by)
            else:
                value = item["group"].get(sort_by)

            if value is None:
                return (1, 0)
            return (0, value)

        rows.sort(key=sort_key, reverse=reverse)
        return rows

    @staticmethod
    def normalize_route_filter(raw_filter):
        if raw_filter in (None, ""):
            return None

        if isinstance(raw_filter, str):
            normalized = raw_filter.strip().lower()
            if not normalized:
                return None
            if normalized.isdigit():
                raw_filter = int(normalized)
            elif normalized in RouteAnalyticsService.ALLOWED_PREFERENCES:
                return normalized
            else:
                return None

        try:
            enum_value = int(raw_filter)
        except (TypeError, ValueError):
            return None

        return RouteAnalyticsService.FILTER_ENUM_TO_PREFERENCE.get(enum_value)

    @staticmethod
    def apply_filters(queryset, query_params):
        source = query_params.get("source")
        status_value = query_params.get("status")
        route_filter = RouteAnalyticsService.normalize_route_filter(
            query_params.get("filter")
        )
        from_date = query_params.get("from_date")
        to_date = query_params.get("to_date")

        if source in {RouteHistory.SOURCE_TEXT, RouteHistory.SOURCE_MAP}:
            queryset = queryset.filter(source_type=source)

        if status_value in {RouteHistory.STATUS_SUCCESS, RouteHistory.STATUS_FAILED}:
            queryset = queryset.filter(status=status_value)

        if route_filter is not None:
            queryset = queryset.filter(preference=route_filter)

        if from_date:
            parsed_from = parse_date(from_date)
            if parsed_from:
                queryset = queryset.filter(created_at__date__gte=parsed_from)

        if to_date:
            parsed_to = parse_date(to_date)
            if parsed_to:
                queryset = queryset.filter(created_at__date__lte=parsed_to)

        return queryset

    @staticmethod
    def serialize_applied_filters(query_params):
        return {
            "source": query_params.get("source"),
            "status": query_params.get("status"),
            "filter": RouteAnalyticsService.normalize_route_filter(
                query_params.get("filter")
            ),
            "from_date": query_params.get("from_date"),
            "to_date": query_params.get("to_date"),
        }
