from django.conf import settings
import grpc
import time
from uuid import uuid4
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from src.Infrastructure.History.models import RouteHistory
from src.Infrastructure.GrpcClients.ai_client import AiGrpcClient, AiGrpcClientError
from src.Infrastructure.GrpcClients.routing_client import (
    RoutingGrpcClient,
    RoutingGrpcClientError,
)


class RouteOrchestratorView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client_boot_error = None
        self.ai_client = None
        self.routing_client = None

        try:
            self.ai_client = AiGrpcClient(
                host=settings.AI_GRPC_HOST,
                port=settings.AI_GRPC_PORT,
                timeout_seconds=settings.AI_GRPC_TIMEOUT_SECONDS,
            )
            self.routing_client = RoutingGrpcClient(
                host=settings.ROUTING_GRPC_HOST,
                port=settings.ROUTING_GRPC_PORT,
                timeout_seconds=settings.ROUTING_GRPC_TIMEOUT_SECONDS,
            )
        except RuntimeError as error:
            self.client_boot_error = str(error)

    @staticmethod
    def _parse_coordinates(data):
        try:
            origin = data["origin"]
            destination = data["destination"]

            s_lat = float(origin["lat"])
            s_lon = float(origin["lon"])
            d_lat = float(destination["lat"])
            d_lon = float(destination["lon"])
        except (TypeError, KeyError, ValueError):
            return None

        if not (-90.0 <= s_lat <= 90.0 and -90.0 <= d_lat <= 90.0):
            return None
        if not (-180.0 <= s_lon <= 180.0 and -180.0 <= d_lon <= 180.0):
            return None

        return s_lat, s_lon, d_lat, d_lon

    @staticmethod
    def _error_response(request_id, http_status, error_code, message):
        return Response(
            {
                "request_id": request_id,
                "error": {
                    "code": error_code,
                    "message": message,
                },
            },
            status=http_status,
        )

    @staticmethod
    def _map_ai_error(error):
        if error.code == grpc.StatusCode.INVALID_ARGUMENT:
            return status.HTTP_400_BAD_REQUEST, "AI_INVALID_INPUT"
        if error.code == grpc.StatusCode.NOT_FOUND:
            return status.HTTP_422_UNPROCESSABLE_ENTITY, "AI_LOCATION_NOT_FOUND"
        if error.code == grpc.StatusCode.DEADLINE_EXCEEDED:
            return status.HTTP_504_GATEWAY_TIMEOUT, "AI_TIMEOUT"
        if error.code == grpc.StatusCode.UNAVAILABLE:
            return status.HTTP_503_SERVICE_UNAVAILABLE, "AI_UNAVAILABLE"
        return status.HTTP_502_BAD_GATEWAY, "AI_UPSTREAM_ERROR"

    @staticmethod
    def _map_routing_error(error):
        if error.code == grpc.StatusCode.INVALID_ARGUMENT:
            return status.HTTP_400_BAD_REQUEST, "ROUTING_INVALID_INPUT"
        if error.code == grpc.StatusCode.NOT_FOUND:
            return status.HTTP_404_NOT_FOUND, "ROUTING_NO_PATH"
        if error.code == grpc.StatusCode.DEADLINE_EXCEEDED:
            return status.HTTP_504_GATEWAY_TIMEOUT, "ROUTING_TIMEOUT"
        if error.code == grpc.StatusCode.UNAVAILABLE:
            return status.HTTP_503_SERVICE_UNAVAILABLE, "ROUTING_UNAVAILABLE"
        return status.HTTP_502_BAD_GATEWAY, "ROUTING_UPSTREAM_ERROR"

    @staticmethod
    def _success_response(request_id, source, route_result, from_data, to_data, intent):
        return Response(
            {
                "request_id": request_id,
                "source": source,
                "from": from_data,
                "to": to_data,
                "route": route_result,
                "meta": {
                    "intent": intent,
                    "step_count": len(route_result.get("steps", [])),
                },
            },
            status=status.HTTP_200_OK,
        )

    def _record_history(
        self,
        request,
        source_type,
        input_text,
        from_data,
        to_data,
        route_result,
        status_value,
        error_code,
        error_message,
        ai_latency_ms,
        routing_latency_ms,
        total_latency_ms,
    ):
        user = request.user if request.user.is_authenticated else None
        RouteHistory.objects.create(
            user=user,
            source_type=source_type,
            input_text=input_text,
            origin_name=from_data.get("name") if from_data else None,
            destination_name=to_data.get("name") if to_data else None,
            origin_lat=from_data.get("lat") if from_data else None,
            origin_lon=from_data.get("lon") if from_data else None,
            destination_lat=to_data.get("lat") if to_data else None,
            destination_lon=to_data.get("lon") if to_data else None,
            status=status_value,
            error_code=error_code,
            error_message=error_message,
            total_distance_meters=(
                route_result.get("total_distance_meters") if route_result else None
            ),
            total_duration_seconds=(
                route_result.get("total_duration_seconds") if route_result else None
            ),
            step_count=(len(route_result.get("steps", [])) if route_result else None),
            ai_latency_ms=ai_latency_ms,
            routing_latency_ms=routing_latency_ms,
            total_latency_ms=total_latency_ms,
        )

    def post(self, request):
        request_id = str(uuid4())
        request_start = time.perf_counter()

        if self.client_boot_error:
            total_latency_ms = (time.perf_counter() - request_start) * 1000.0
            self._record_history(
                request=request,
                source_type=RouteHistory.SOURCE_TEXT,
                input_text=request.data.get("text"),
                from_data=None,
                to_data=None,
                route_result=None,
                status_value=RouteHistory.STATUS_FAILED,
                error_code="API_CLIENT_BOOT_ERROR",
                error_message=self.client_boot_error,
                ai_latency_ms=None,
                routing_latency_ms=None,
                total_latency_ms=total_latency_ms,
            )
            return self._error_response(
                request_id,
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "API_CLIENT_BOOT_ERROR",
                self.client_boot_error,
            )

        if self.ai_client is None or self.routing_client is None:
            total_latency_ms = (time.perf_counter() - request_start) * 1000.0
            self._record_history(
                request=request,
                source_type=RouteHistory.SOURCE_TEXT,
                input_text=request.data.get("text"),
                from_data=None,
                to_data=None,
                route_result=None,
                status_value=RouteHistory.STATUS_FAILED,
                error_code="API_CLIENT_UNAVAILABLE",
                error_message="gRPC clients are not available.",
                ai_latency_ms=None,
                routing_latency_ms=None,
                total_latency_ms=total_latency_ms,
            )
            return self._error_response(
                request_id,
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "API_CLIENT_UNAVAILABLE",
                "gRPC clients are not available.",
            )

        data = request.data

        has_text = (
            isinstance(data.get("text"), str) and data.get("text", "").strip() != ""
        )
        has_coordinates = "origin" in data and "destination" in data

        if has_text and has_coordinates:
            total_latency_ms = (time.perf_counter() - request_start) * 1000.0
            self._record_history(
                request=request,
                source_type=RouteHistory.SOURCE_TEXT,
                input_text=data.get("text"),
                from_data=None,
                to_data=None,
                route_result=None,
                status_value=RouteHistory.STATUS_FAILED,
                error_code="INVALID_REQUEST_MODE",
                error_message="Provide either text or origin/destination, not both.",
                ai_latency_ms=None,
                routing_latency_ms=None,
                total_latency_ms=total_latency_ms,
            )
            return self._error_response(
                request_id,
                status.HTTP_400_BAD_REQUEST,
                "INVALID_REQUEST_MODE",
                "Provide either text or origin/destination, not both.",
            )

        if has_coordinates:
            source_type = RouteHistory.SOURCE_MAP
            parsed = self._parse_coordinates(data)
            if parsed is None:
                total_latency_ms = (time.perf_counter() - request_start) * 1000.0
                self._record_history(
                    request=request,
                    source_type=source_type,
                    input_text=None,
                    from_data=None,
                    to_data=None,
                    route_result=None,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code="INVALID_COORDINATES",
                    error_message="Invalid coordinate format.",
                    ai_latency_ms=None,
                    routing_latency_ms=None,
                    total_latency_ms=total_latency_ms,
                )
                return self._error_response(
                    request_id,
                    status.HTTP_400_BAD_REQUEST,
                    "INVALID_COORDINATES",
                    "Invalid coordinate format.",
                )

            s_lat, s_lon, d_lat, d_lon = parsed
            from_data = {"name": None, "lat": s_lat, "lon": s_lon}
            to_data = {"name": None, "lat": d_lat, "lon": d_lon}

            routing_start = time.perf_counter()
            try:
                route_result = self.routing_client.get_route(
                    s_lat,
                    s_lon,
                    d_lat,
                    d_lon,
                )
            except RoutingGrpcClientError as error:
                routing_latency_ms = (time.perf_counter() - routing_start) * 1000.0
                total_latency_ms = (time.perf_counter() - request_start) * 1000.0
                http_status, error_code = self._map_routing_error(error)
                self._record_history(
                    request=request,
                    source_type=source_type,
                    input_text=None,
                    from_data=from_data,
                    to_data=to_data,
                    route_result=None,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code=error_code,
                    error_message=error.details,
                    ai_latency_ms=None,
                    routing_latency_ms=routing_latency_ms,
                    total_latency_ms=total_latency_ms,
                )
                return self._error_response(
                    request_id,
                    http_status,
                    error_code,
                    error.details,
                )

            routing_latency_ms = (time.perf_counter() - routing_start) * 1000.0
            total_latency_ms = (time.perf_counter() - request_start) * 1000.0
            self._record_history(
                request=request,
                source_type=source_type,
                input_text=None,
                from_data=from_data,
                to_data=to_data,
                route_result=route_result,
                status_value=RouteHistory.STATUS_SUCCESS,
                error_code=None,
                error_message=None,
                ai_latency_ms=None,
                routing_latency_ms=routing_latency_ms,
                total_latency_ms=total_latency_ms,
            )

            return self._success_response(
                request_id=request_id,
                source="map",
                route_result=route_result,
                from_data=from_data,
                to_data=to_data,
                intent="direct_coordinates",
            )

        if has_text:
            source_type = RouteHistory.SOURCE_TEXT
            text_query = data["text"].strip()
            ai_start = time.perf_counter()
            try:
                ai_result = self.ai_client.extract_route(text_query)
            except AiGrpcClientError as error:
                ai_latency_ms = (time.perf_counter() - ai_start) * 1000.0
                total_latency_ms = (time.perf_counter() - request_start) * 1000.0
                http_status, error_code = self._map_ai_error(error)
                self._record_history(
                    request=request,
                    source_type=source_type,
                    input_text=text_query,
                    from_data=None,
                    to_data=None,
                    route_result=None,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code=error_code,
                    error_message=error.details,
                    ai_latency_ms=ai_latency_ms,
                    routing_latency_ms=None,
                    total_latency_ms=total_latency_ms,
                )
                return self._error_response(
                    request_id,
                    http_status,
                    error_code,
                    error.details,
                )

            ai_latency_ms = (time.perf_counter() - ai_start) * 1000.0

            if not ai_result:
                total_latency_ms = (time.perf_counter() - request_start) * 1000.0
                self._record_history(
                    request=request,
                    source_type=source_type,
                    input_text=text_query,
                    from_data=None,
                    to_data=None,
                    route_result=None,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code="AI_EMPTY_RESULT",
                    error_message="AI service returned no coordinates.",
                    ai_latency_ms=ai_latency_ms,
                    routing_latency_ms=None,
                    total_latency_ms=total_latency_ms,
                )
                return self._error_response(
                    request_id,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "AI_EMPTY_RESULT",
                    "AI service returned no coordinates.",
                )

            from_data = {
                "name": ai_result.get("from_location"),
                "lat": ai_result["from_lat"],
                "lon": ai_result["from_lon"],
            }
            to_data = {
                "name": ai_result.get("to_location"),
                "lat": ai_result["to_lat"],
                "lon": ai_result["to_lon"],
            }

            routing_start = time.perf_counter()
            try:
                route_result = self.routing_client.get_route(
                    ai_result["from_lat"],
                    ai_result["from_lon"],
                    ai_result["to_lat"],
                    ai_result["to_lon"],
                )
            except RoutingGrpcClientError as error:
                routing_latency_ms = (time.perf_counter() - routing_start) * 1000.0
                total_latency_ms = (time.perf_counter() - request_start) * 1000.0
                http_status, error_code = self._map_routing_error(error)
                self._record_history(
                    request=request,
                    source_type=source_type,
                    input_text=text_query,
                    from_data=from_data,
                    to_data=to_data,
                    route_result=None,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code=error_code,
                    error_message=error.details,
                    ai_latency_ms=ai_latency_ms,
                    routing_latency_ms=routing_latency_ms,
                    total_latency_ms=total_latency_ms,
                )
                return self._error_response(
                    request_id,
                    http_status,
                    error_code,
                    error.details,
                )

            routing_latency_ms = (time.perf_counter() - routing_start) * 1000.0
            total_latency_ms = (time.perf_counter() - request_start) * 1000.0
            self._record_history(
                request=request,
                source_type=source_type,
                input_text=text_query,
                from_data=from_data,
                to_data=to_data,
                route_result=route_result,
                status_value=RouteHistory.STATUS_SUCCESS,
                error_code=None,
                error_message=None,
                ai_latency_ms=ai_latency_ms,
                routing_latency_ms=routing_latency_ms,
                total_latency_ms=total_latency_ms,
            )

            return self._success_response(
                request_id=request_id,
                source="text",
                route_result=route_result,
                from_data=from_data,
                to_data=to_data,
                intent=ai_result.get("intent", "unknown"),
            )

        total_latency_ms = (time.perf_counter() - request_start) * 1000.0
        self._record_history(
            request=request,
            source_type=RouteHistory.SOURCE_TEXT,
            input_text=data.get("text"),
            from_data=None,
            to_data=None,
            route_result=None,
            status_value=RouteHistory.STATUS_FAILED,
            error_code="INVALID_REQUEST_BODY",
            error_message="Provide either 'text' or both 'origin' and 'destination'.",
            ai_latency_ms=None,
            routing_latency_ms=None,
            total_latency_ms=total_latency_ms,
        )
        return self._error_response(
            request_id,
            status.HTTP_400_BAD_REQUEST,
            "INVALID_REQUEST_BODY",
            "Provide either 'text' or both 'origin' and 'destination'.",
        )
