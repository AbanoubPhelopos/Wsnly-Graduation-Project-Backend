from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from django.conf import settings
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.utils.dateparse import parse_date
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
from src.Infrastructure.History.models import RouteHistory
from src.Presentation.schemas import (
    ChangeUserRoleRequestSerializer,
    MessageResponseSerializer,
    UserSummarySerializer,
    ValidationErrorsResponseSerializer,
)


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
        source = request.query_params.get("source")
        status_value = request.query_params.get("status")
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")

        if source in {RouteHistory.SOURCE_TEXT, RouteHistory.SOURCE_MAP}:
            queryset = queryset.filter(source_type=source)

        if status_value in {RouteHistory.STATUS_SUCCESS, RouteHistory.STATUS_FAILED}:
            queryset = queryset.filter(status=status_value)

        if from_date:
            parsed_from = parse_date(from_date)
            if parsed_from:
                queryset = queryset.filter(created_at__date__gte=parsed_from)

        if to_date:
            parsed_to = parse_date(to_date)
            if parsed_to:
                queryset = queryset.filter(created_at__date__lte=parsed_to)

        return queryset


class RouteAnalyticsOverviewView(RouteAnalyticsBaseView):
    @extend_schema(
        tags=["Admin Analytics"],
        summary="Route analytics overview",
        parameters=[
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
                name="from_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="to_date", type=OpenApiTypes.DATE, location=OpenApiParameter.QUERY
            ),
        ],
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
                "filters": {
                    "source": request.query_params.get("source"),
                    "status": request.query_params.get("status"),
                    "from_date": request.query_params.get("from_date"),
                    "to_date": request.query_params.get("to_date"),
                },
            },
            status=status.HTTP_200_OK,
        )


class RouteAnalyticsTopRoutesView(RouteAnalyticsBaseView):
    @extend_schema(
        tags=["Admin Analytics"],
        summary="Top requested routes",
        parameters=[
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
                name="from_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="to_date", type=OpenApiTypes.DATE, location=OpenApiParameter.QUERY
            ),
        ],
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
                "filters": {
                    "source": request.query_params.get("source"),
                    "status": request.query_params.get("status"),
                    "from_date": request.query_params.get("from_date"),
                    "to_date": request.query_params.get("to_date"),
                },
            },
            status=status.HTTP_200_OK,
        )


class RouteSelectionStatsView(RouteAnalyticsBaseView):
    @extend_schema(
        tags=["Admin Analytics"],
        summary="Selected route type statistics",
        parameters=[
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
                name="from_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="to_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: inline_serializer(
                name="RouteSelectionStatsResponse",
                fields={
                    "selections": serializers.ListField(child=serializers.DictField()),
                    "filters": serializers.DictField(),
                },
            )
        },
    )
    def get(self, request):
        queryset = self._apply_filters(
            RouteHistory.objects.filter(has_result=True), request
        )

        selections = (
            queryset.exclude(selected_route_type__isnull=True)
            .values("selected_route_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return Response(
            {
                "selections": list(selections),
                "filters": {
                    "source": request.query_params.get("source"),
                    "status": request.query_params.get("status"),
                    "from_date": request.query_params.get("from_date"),
                    "to_date": request.query_params.get("to_date"),
                },
            },
            status=status.HTTP_200_OK,
        )


class RouteUnresolvedStatsView(RouteAnalyticsBaseView):
    @extend_schema(
        tags=["Admin Analytics"],
        summary="Unresolved and long-walk route statistics",
        parameters=[
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
                name="from_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="to_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
        ],
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
                "filters": {
                    "source": request.query_params.get("source"),
                    "status": request.query_params.get("status"),
                    "from_date": request.query_params.get("from_date"),
                    "to_date": request.query_params.get("to_date"),
                },
            },
            status=status.HTTP_200_OK,
        )
