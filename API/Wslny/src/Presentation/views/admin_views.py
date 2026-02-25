from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from django.conf import settings
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from src.Presentation.permissions import IsAdminUser
from src.Core.Application.Admin.Commands.ChangeUserRoleCommand import (
    ChangeUserRoleCommand,
    ChangeUserRoleCommandHandler,
)
from src.Core.Application.Admin.Queries.GetUsersQuery import (
    GetUsersQuery,
    GetUsersQueryHandler,
)
from src.Core.Application.Admin.Services.RouteAnalyticsService import (
    RouteAnalyticsService,
)
from src.Infrastructure.History.models import RouteHistory
from src.Presentation.schemas import (
    ChangeUserRoleRequestSerializer,
    MessageResponseSerializer,
    UserSummarySerializer,
    ValidationErrorsResponseSerializer,
)


ROUTE_ANALYTICS_QUERY_PARAMETERS = [
    OpenApiParameter(
        name="source",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        enum=["text", "map"],
    ),
    OpenApiParameter(
        name="status",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        enum=["success", "failed"],
    ),
    OpenApiParameter(
        name="filter",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description=(
            "Route filter name or enum value: optimal/fastest/cheapest/"
            "bus_only/microbus_only/metro_only or 1..6"
        ),
    ),
    OpenApiParameter(
        name="from_date",
        type=OpenApiTypes.DATE,
        location=OpenApiParameter.QUERY,
    ),
    OpenApiParameter(
        name="to_date",
        type=OpenApiTypes.DATE,
        location=OpenApiParameter.QUERY,
    ),
]

ROUTE_ANALYTICS_GENERIC_QUERY_PARAMETERS = ROUTE_ANALYTICS_QUERY_PARAMETERS + [
    OpenApiParameter(
        name="metrics",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description=(
            "Comma-separated metrics. Available: requests, success_count, failed_count, "
            "success_rate_percent, avg_total_latency_ms, avg_ai_latency_ms, "
            "avg_routing_latency_ms, avg_duration_seconds, avg_distance_meters, "
            "avg_fare, unresolved_count, unresolved_rate_percent, "
            "long_walk_count, long_walk_rate_percent"
        ),
    ),
    OpenApiParameter(
        name="group_by",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description=(
            "Comma-separated grouping fields. Available: day, week, source, status, "
            "filter, selected_route_type"
        ),
    ),
    OpenApiParameter(
        name="sort",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Sort field from selected metrics or group_by fields.",
    ),
    OpenApiParameter(
        name="order",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        enum=["asc", "desc"],
    ),
    OpenApiParameter(
        name="limit",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Pagination limit (1..200).",
    ),
    OpenApiParameter(
        name="offset",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Pagination offset (>=0).",
    ),
]


class ChangeUserRoleView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin"],
        summary="Change user role",
        request=ChangeUserRoleRequestSerializer,
        responses={
            200: OpenApiResponse(response=MessageResponseSerializer),
            400: OpenApiResponse(response=ValidationErrorsResponseSerializer),
            403: OpenApiResponse(description="Forbidden"),
        },
    )
    def post(self, request):
        command = ChangeUserRoleCommand(
            user_id=request.data.get("user_id"), new_role=request.data.get("new_role")
        )

        handler = ChangeUserRoleCommandHandler()
        result = handler.handle(command)

        if result.is_success:
            return Response(
                {"message": "Role updated successfully"}, status=status.HTTP_200_OK
            )

        return Response(
            {"errors": [vars(e) for e in result.errors]},
            status=status.HTTP_400_BAD_REQUEST,
        )


class UserListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin"],
        summary="List users",
        responses={
            200: UserSummarySerializer(many=True),
            400: OpenApiResponse(response=ValidationErrorsResponseSerializer),
            403: OpenApiResponse(description="Forbidden"),
        },
    )
    def get(self, request):
        query = GetUsersQuery()
        handler = GetUsersQueryHandler()
        result = handler.handle(query)

        if result.is_success:
            return Response([vars(u) for u in result.data], status=status.HTTP_200_OK)

        return Response(
            {"errors": [vars(e) for e in result.errors]},
            status=status.HTTP_400_BAD_REQUEST,
        )


class RouteAnalyticsBaseView(APIView):
    permission_classes = [IsAdminUser]

    @staticmethod
    def _apply_filters(queryset, request):
        return RouteAnalyticsService.apply_filters(queryset, request.query_params)

    @staticmethod
    def _serialize_filters(request):
        return RouteAnalyticsService.serialize_applied_filters(request.query_params)


class RouteAnalyticsOverviewView(RouteAnalyticsBaseView):
    @extend_schema(
        tags=["Admin Analytics"],
        summary="Route analytics overview",
        parameters=ROUTE_ANALYTICS_QUERY_PARAMETERS,
        responses={
            200: inline_serializer(
                name="RouteAnalyticsOverviewResponse",
                fields={
                    "totals": serializers.DictField(),
                    "source_breakdown": serializers.DictField(),
                    "averages": serializers.DictField(),
                    "daily_usage": serializers.ListField(child=serializers.DictField()),
                    "filters": serializers.DictField(),
                },
            )
        },
    )
    def get(self, request):
        queryset = self._apply_filters(RouteHistory.objects.all(), request)
        total_requests = queryset.count()
        success_count = queryset.filter(status=RouteHistory.STATUS_SUCCESS).count()
        failed_count = total_requests - success_count

        source_counts = queryset.values("source_type").annotate(count=Count("id"))
        source_breakdown = {
            item["source_type"]: item["count"] for item in source_counts
        }

        latency = queryset.aggregate(
            avg_ai_latency_ms=Avg("ai_latency_ms"),
            avg_routing_latency_ms=Avg("routing_latency_ms"),
            avg_total_latency_ms=Avg("total_latency_ms"),
            avg_duration_seconds=Avg("total_duration_seconds"),
            avg_distance_meters=Avg("total_distance_meters"),
        )

        daily_usage = list(
            queryset.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )

        success_rate = (
            (success_count / total_requests * 100.0) if total_requests else 0.0
        )

        return Response(
            {
                "totals": {
                    "requests": total_requests,
                    "success": success_count,
                    "failed": failed_count,
                    "success_rate_percent": round(success_rate, 2),
                },
                "source_breakdown": {
                    RouteHistory.SOURCE_TEXT: source_breakdown.get(
                        RouteHistory.SOURCE_TEXT, 0
                    ),
                    RouteHistory.SOURCE_MAP: source_breakdown.get(
                        RouteHistory.SOURCE_MAP, 0
                    ),
                },
                "averages": {
                    "ai_latency_ms": latency["avg_ai_latency_ms"],
                    "routing_latency_ms": latency["avg_routing_latency_ms"],
                    "total_latency_ms": latency["avg_total_latency_ms"],
                    "duration_seconds": latency["avg_duration_seconds"],
                    "distance_meters": latency["avg_distance_meters"],
                },
                "daily_usage": daily_usage,
                "filters": self._serialize_filters(request),
            },
            status=status.HTTP_200_OK,
        )


class RouteAnalyticsTopRoutesView(RouteAnalyticsBaseView):
    @extend_schema(
        tags=["Admin Analytics"],
        summary="Top requested routes",
        parameters=ROUTE_ANALYTICS_QUERY_PARAMETERS,
        responses={
            200: inline_serializer(
                name="RouteAnalyticsTopRoutesResponse",
                fields={
                    "top_routes": serializers.ListField(child=serializers.DictField()),
                    "filters": serializers.DictField(),
                },
            )
        },
    )
    def get(self, request):
        queryset = self._apply_filters(
            RouteHistory.objects.filter(status=RouteHistory.STATUS_SUCCESS),
            request,
        )

        top_pairs = list(
            queryset.exclude(origin_name__isnull=True)
            .exclude(destination_name__isnull=True)
            .values("origin_name", "destination_name")
            .annotate(
                requests=Count("id"),
                avg_duration_seconds=Avg("total_duration_seconds"),
                avg_distance_meters=Avg("total_distance_meters"),
            )
            .order_by("-requests")[:10]
        )

        return Response(
            {
                "top_routes": top_pairs,
                "filters": self._serialize_filters(request),
            },
            status=status.HTTP_200_OK,
        )


class RouteFilterStatsView(RouteAnalyticsBaseView):
    @extend_schema(
        tags=["Admin Analytics"],
        summary="Per-user route filter statistics",
        parameters=ROUTE_ANALYTICS_QUERY_PARAMETERS,
        responses={
            200: inline_serializer(
                name="RouteFilterStatsResponse",
                fields={
                    "by_filter": serializers.ListField(child=serializers.DictField()),
                    "by_user_filter": serializers.ListField(
                        child=serializers.DictField()
                    ),
                    "filters": serializers.DictField(),
                },
            )
        },
    )
    def get(self, request):
        queryset = self._apply_filters(
            RouteHistory.objects.filter(has_result=True), request
        )

        by_filter = (
            queryset.values("preference").annotate(count=Count("id")).order_by("-count")
        )

        by_user_filter = (
            queryset.exclude(user__isnull=True)
            .values("user_id", "user__email", "preference")
            .annotate(
                count=Count("id"),
                avg_duration_seconds=Avg("total_duration_seconds"),
                avg_fare=Avg("estimated_fare"),
            )
            .order_by("user_id", "-count")
        )

        return Response(
            {
                "by_filter": list(by_filter),
                "by_user_filter": list(by_user_filter),
                "filters": self._serialize_filters(request),
            },
            status=status.HTTP_200_OK,
        )


class RouteUnresolvedStatsView(RouteAnalyticsBaseView):
    @extend_schema(
        tags=["Admin Analytics"],
        summary="Unresolved and long-walk route statistics",
        parameters=ROUTE_ANALYTICS_QUERY_PARAMETERS,
        responses={
            200: inline_serializer(
                name="RouteUnresolvedStatsResponse",
                fields={
                    "unresolved_reasons": serializers.ListField(
                        child=serializers.DictField()
                    ),
                    "long_walk_count": serializers.IntegerField(),
                    "top_unresolved_queries": serializers.ListField(
                        child=serializers.DictField()
                    ),
                    "filters": serializers.DictField(),
                },
            )
        },
    )
    def get(self, request):
        queryset = self._apply_filters(RouteHistory.objects.all(), request)

        unresolved = list(
            queryset.filter(has_result=False)
            .exclude(unresolved_reason__isnull=True)
            .exclude(unresolved_reason="")
            .values("unresolved_reason")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        long_walk = queryset.filter(
            walk_distance_meters__isnull=False,
            walk_distance_meters__gte=settings.ROUTE_LONG_WALK_THRESHOLD_METERS,
        ).count()

        unresolved_queries = list(
            queryset.filter(has_result=False)
            .exclude(input_text__isnull=True)
            .values("input_text", "error_code")
            .annotate(count=Count("id"))
            .order_by("-count")[:20]
        )

        return Response(
            {
                "unresolved_reasons": unresolved,
                "long_walk_count": long_walk,
                "top_unresolved_queries": unresolved_queries,
                "filters": self._serialize_filters(request),
            },
            status=status.HTTP_200_OK,
        )


class RouteAnalyticsQueryView(RouteAnalyticsBaseView):
    @extend_schema(
        tags=["Admin Analytics"],
        summary="Generic route analytics query",
        parameters=ROUTE_ANALYTICS_GENERIC_QUERY_PARAMETERS,
        responses={
            200: inline_serializer(
                name="RouteAnalyticsQueryResponse",
                fields={
                    "rows": serializers.ListField(child=serializers.DictField()),
                    "meta": serializers.DictField(),
                    "filters": serializers.DictField(),
                },
            )
        },
    )
    def get(self, request):
        queryset = self._apply_filters(RouteHistory.objects.all(), request)

        metrics = RouteAnalyticsService.parse_metrics(
            request.query_params.get("metrics")
        )
        group_by = RouteAnalyticsService.parse_group_by(
            request.query_params.get("group_by")
        )
        limit, offset = RouteAnalyticsService.parse_pagination(
            request.query_params.get("limit"),
            request.query_params.get("offset"),
        )
        sort_by, order = RouteAnalyticsService.parse_sorting(
            request.query_params.get("sort"),
            request.query_params.get("order"),
            group_by,
            metrics,
        )

        rows = RouteAnalyticsService.query_analytics(queryset, metrics, group_by)
        rows = RouteAnalyticsService.sort_rows(rows, sort_by, order)

        total_rows = len(rows)
        paginated_rows = rows[offset : offset + limit]

        return Response(
            {
                "rows": paginated_rows,
                "meta": {
                    "metrics": metrics,
                    "group_by": group_by,
                    "sort": sort_by,
                    "order": order,
                    "limit": limit,
                    "offset": offset,
                    "total_rows": total_rows,
                },
                "filters": self._serialize_filters(request),
            },
            status=status.HTTP_200_OK,
        )
