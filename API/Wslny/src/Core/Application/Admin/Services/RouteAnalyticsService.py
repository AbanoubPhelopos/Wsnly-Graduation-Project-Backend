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
