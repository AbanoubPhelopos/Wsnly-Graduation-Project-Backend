from django.conf import settings
import grpc
import time
from uuid import uuid4
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    PolymorphicProxySerializer,
    extend_schema,
)
from src.Infrastructure.History.models import RouteHistory
from src.Infrastructure.GrpcClients.ai_client import AiGrpcClient, AiGrpcClientError
from src.Infrastructure.GrpcClients.routing_client import (
    RoutingGrpcClient,
    RoutingGrpcClientError,
)
from src.Presentation.schemas import (
    MapRouteRequestSerializer,
    RouteErrorResponseSerializer,
    RouteHistoryItemSerializer,
    RouteSuccessResponseSerializer,
    TextRouteRequestSerializer,
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
    def _parse_current_location(data):
        if "current_location" not in data:
            return None

        try:
            current = data["current_location"]
            lat = float(current["lat"])
            lon = float(current["lon"])
        except (TypeError, KeyError, ValueError):
            return None

        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return None

        return lat, lon

    @staticmethod
    def _parse_filter(data):
        route_filter = str(data.get("filter") or data.get("preference") or "optimal")
        route_filter = route_filter.strip().lower()
        if route_filter not in {
            RouteHistory.PREFERENCE_OPTIMAL,
            RouteHistory.PREFERENCE_FASTEST,
            RouteHistory.PREFERENCE_CHEAPEST,
            RouteHistory.PREFERENCE_BUS_ONLY,
            RouteHistory.PREFERENCE_MICROBUS_ONLY,
            RouteHistory.PREFERENCE_METRO_ONLY,
        }:
            return RouteHistory.PREFERENCE_OPTIMAL
        return route_filter

    @staticmethod
    def _metro_fare_by_stops(stops_count):
        for max_stops, fare in settings.ROUTE_METRO_FARE_TIERS:
            if stops_count <= max_stops:
                return fare
        return settings.ROUTE_METRO_FARE_TIERS[-1][1]

    @staticmethod
    def _compute_route_cost(route_option):
        metro_stops = 0
        bus_rides = 0
        microbus_rides = 0
        walk_distance = 0.0
        transport_segments = 0

        for segment in route_option.get("segments", []):
            method = (segment.get("method") or "").lower()
            if method == "walking":
                walk_distance += float(segment.get("distanceMeters", 0) or 0)
                continue

            transport_segments += 1

            if method == "metro":
                metro_stops += int(segment.get("numStops", 0) or 0)
            elif method == "bus":
                bus_rides += 1
            elif method == "microbus":
                microbus_rides += 1

        estimated_fare = 0.0
        if metro_stops > 0:
            estimated_fare += RouteOrchestratorView._metro_fare_by_stops(metro_stops)
        if bus_rides > 0:
            estimated_fare += bus_rides * settings.ROUTE_BUS_FARE_PER_RIDE
        if microbus_rides > 0:
            estimated_fare += microbus_rides * settings.ROUTE_MICROBUS_FARE_PER_RIDE

        route_option["estimatedFare"] = estimated_fare
        route_option["walkDistanceMeters"] = walk_distance
        route_option["transportSegments"] = transport_segments

    @staticmethod
    def _select_route(route_result, route_filter):
        if "routes" not in route_result:
            return route_result, None

        routes = list(route_result.get("routes", []))
        for option in routes:
            RouteOrchestratorView._compute_route_cost(option)
        found_routes = [option for option in routes if option.get("found")]
        if not found_routes:
            ordered_result = dict(route_result)
            ordered_result["routes"] = routes
            return ordered_result, None

        def duration_key(option):
            return int(option.get("totalDurationSeconds", 10**9) or 10**9)

        def cheapest_key(option):
            fare = option.get("estimatedFare")
            return float(fare if fare is not None else 10**9), duration_key(option)

        if route_filter == RouteHistory.PREFERENCE_FASTEST:
            selected = min(found_routes, key=duration_key)
        elif route_filter == RouteHistory.PREFERENCE_CHEAPEST:
            selected = min(found_routes, key=cheapest_key)
        elif route_filter == RouteHistory.PREFERENCE_BUS_ONLY:
            selected = next(
                (
                    option
                    for option in found_routes
                    if option.get("type") == RouteHistory.PREFERENCE_BUS_ONLY
                ),
                None,
            )
        elif route_filter == RouteHistory.PREFERENCE_MICROBUS_ONLY:
            selected = next(
                (
                    option
                    for option in found_routes
                    if option.get("type") == RouteHistory.PREFERENCE_MICROBUS_ONLY
                ),
                None,
            )
        elif route_filter == RouteHistory.PREFERENCE_METRO_ONLY:
            selected = next(
                (
                    option
                    for option in found_routes
                    if option.get("type") == RouteHistory.PREFERENCE_METRO_ONLY
                ),
                None,
            )
        elif route_filter == RouteHistory.PREFERENCE_OPTIMAL:
            selected = min(
                found_routes,
                key=lambda option: (
                    int(option.get("transportSegments", 10**9) or 10**9),
                    duration_key(option),
                ),
            )
        else:
            selected = None

        ordered_result = dict(route_result)
        ordered_result["routes"] = routes
        return ordered_result, selected

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
    def _success_response(
        request_id,
        source,
        route_result,
        from_data,
        to_data,
        intent,
        route_filter,
        selected_route,
    ):
        payload = {
            "request_id": request_id,
            "source": source,
            "intent": intent,
            "filter": route_filter,
            "from_name": from_data.get("name") if from_data else None,
            "to_name": to_data.get("name") if to_data else None,
        }

        if "query" in route_result and "routes" in route_result:
            payload["query"] = route_result["query"]
            payload["route"] = selected_route
        else:
            payload["query"] = {
                "origin": {
                    "lat": from_data.get("lat") if from_data else None,
                    "lon": from_data.get("lon") if from_data else None,
                },
                "destination": {
                    "lat": to_data.get("lat") if to_data else None,
                    "lon": to_data.get("lon") if to_data else None,
                },
            }
            payload["route"] = {
                "type": "optimal",
                "found": True,
                "totalDurationSeconds": int(
                    route_result.get("total_duration_seconds", 0)
                ),
                "totalDurationFormatted": "",
                "totalSegments": len(route_result.get("steps", [])),
                "totalDistanceMeters": route_result.get("total_distance_meters", 0.0),
                "segments": [],
            }

        return Response(
            payload,
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _extract_history_summary(selected_route):
        if not selected_route:
            return None, None, None, None, None, False
        return (
            selected_route.get("totalDistanceMeters"),
            selected_route.get("totalDurationSeconds"),
            selected_route.get("totalSegments"),
            selected_route.get("estimatedFare"),
            selected_route.get("walkDistanceMeters"),
            bool(selected_route.get("found")),
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
        request_id=None,
        preference=RouteHistory.PREFERENCE_OPTIMAL,
        selected_route_type=None,
        selected_route=None,
        unresolved_reason=None,
    ):
        user = request.user if request.user.is_authenticated else None
        (
            total_distance,
            total_duration,
            total_steps,
            estimated_fare,
            walk_distance,
            has_result,
        ) = self._extract_history_summary(selected_route)

        RouteHistory.objects.create(
            user=user,
            request_id=request_id,
            source_type=source_type,
            input_text=input_text,
            preference=preference,
            selected_route_type=selected_route_type,
            origin_name=from_data.get("name") if from_data else None,
            destination_name=to_data.get("name") if to_data else None,
            origin_lat=from_data.get("lat") if from_data else None,
            origin_lon=from_data.get("lon") if from_data else None,
            destination_lat=to_data.get("lat") if to_data else None,
            destination_lon=to_data.get("lon") if to_data else None,
            status=status_value,
            error_code=error_code,
            error_message=error_message,
            total_distance_meters=total_distance,
            total_duration_seconds=total_duration,
            step_count=total_steps,
            estimated_fare=estimated_fare,
            walk_distance_meters=walk_distance,
            has_result=has_result,
            unresolved_reason=unresolved_reason,
            ai_latency_ms=ai_latency_ms,
            routing_latency_ms=routing_latency_ms,
            total_latency_ms=total_latency_ms,
        )

    @extend_schema(
        tags=["Routing"],
        summary="Get route by text or map pins",
        description="Send either natural language text or exact origin/destination coordinates.",
        request=PolymorphicProxySerializer(
            component_name="RouteRequest",
            serializers=[TextRouteRequestSerializer, MapRouteRequestSerializer],
            resource_type_field_name=None,
        ),
        responses={
            200: RouteSuccessResponseSerializer,
            400: OpenApiResponse(response=RouteErrorResponseSerializer),
            401: OpenApiResponse(response=RouteErrorResponseSerializer),
            404: OpenApiResponse(response=RouteErrorResponseSerializer),
            422: OpenApiResponse(response=RouteErrorResponseSerializer),
            503: OpenApiResponse(response=RouteErrorResponseSerializer),
            504: OpenApiResponse(response=RouteErrorResponseSerializer),
        },
        examples=[
            OpenApiExample(
                "Text Request",
                value={"text": "عايز اروح العباسيه من مسكن"},
                request_only=True,
            ),
            OpenApiExample(
                "Map Request",
                value={
                    "origin": {"lat": 30.0539, "lon": 31.2383},
                    "destination": {"lat": 30.0735, "lon": 31.2823},
                },
                request_only=True,
            ),
            OpenApiExample(
                "Error Response",
                value={
                    "request_id": "5bb91977-11bf-476f-9fdb-7af8a6589b46",
                    "error": {
                        "code": "AI_LOCATION_NOT_FOUND",
                        "message": "could not geocode one or more locations",
                    },
                },
                response_only=True,
                status_codes=["422"],
            ),
        ],
    )
    def post(self, request):
        request_id = str(uuid4())
        request_start = time.perf_counter()

        if self.client_boot_error:
            total_latency_ms = (time.perf_counter() - request_start) * 1000.0
            self._record_history(
                request=request,
                request_id=request_id,
                source_type=RouteHistory.SOURCE_TEXT,
                input_text=request.data.get("text"),
                preference=RouteHistory.PREFERENCE_OPTIMAL,
                from_data=None,
                to_data=None,
                route_result=None,
                status_value=RouteHistory.STATUS_FAILED,
                error_code="API_CLIENT_BOOT_ERROR",
                error_message=self.client_boot_error,
                unresolved_reason="api_boot_error",
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
                request_id=request_id,
                source_type=RouteHistory.SOURCE_TEXT,
                input_text=request.data.get("text"),
                preference=RouteHistory.PREFERENCE_OPTIMAL,
                from_data=None,
                to_data=None,
                route_result=None,
                status_value=RouteHistory.STATUS_FAILED,
                error_code="API_CLIENT_UNAVAILABLE",
                error_message="gRPC clients are not available.",
                unresolved_reason="api_client_unavailable",
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
        route_filter = self._parse_filter(data)

        has_text = (
            isinstance(data.get("text"), str) and data.get("text", "").strip() != ""
        )
        has_coordinates = "origin" in data and "destination" in data
        current_location = self._parse_current_location(data)

        if has_text and has_coordinates:
            total_latency_ms = (time.perf_counter() - request_start) * 1000.0
            self._record_history(
                request=request,
                request_id=request_id,
                source_type=RouteHistory.SOURCE_TEXT,
                input_text=data.get("text"),
                preference=route_filter,
                from_data=None,
                to_data=None,
                route_result=None,
                status_value=RouteHistory.STATUS_FAILED,
                error_code="INVALID_REQUEST_MODE",
                error_message="Provide either text or origin/destination, not both.",
                selected_route_type=None,
                unresolved_reason="invalid_request_mode",
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
                    request_id=request_id,
                    source_type=source_type,
                    input_text=None,
                    preference=route_filter,
                    from_data=None,
                    to_data=None,
                    route_result=None,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code="INVALID_COORDINATES",
                    error_message="Invalid coordinate format.",
                    selected_route_type=None,
                    unresolved_reason="invalid_coordinates",
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
                route_result = self.routing_client.get_route(s_lat, s_lon, d_lat, d_lon)
            except RoutingGrpcClientError as error:
                routing_latency_ms = (time.perf_counter() - routing_start) * 1000.0
                total_latency_ms = (time.perf_counter() - request_start) * 1000.0
                http_status, error_code = self._map_routing_error(error)
                self._record_history(
                    request=request,
                    request_id=request_id,
                    source_type=source_type,
                    input_text=None,
                    preference=route_filter,
                    from_data=from_data,
                    to_data=to_data,
                    route_result=None,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code=error_code,
                    error_message=error.details,
                    selected_route_type=None,
                    unresolved_reason="routing_error",
                    ai_latency_ms=None,
                    routing_latency_ms=routing_latency_ms,
                    total_latency_ms=total_latency_ms,
                )
                return self._error_response(
                    request_id, http_status, error_code, error.details
                )

            route_result, selected_route = self._select_route(
                route_result, route_filter
            )
            if selected_route is None:
                routing_latency_ms = (time.perf_counter() - routing_start) * 1000.0
                total_latency_ms = (time.perf_counter() - request_start) * 1000.0
                self._record_history(
                    request=request,
                    request_id=request_id,
                    source_type=source_type,
                    input_text=None,
                    preference=route_filter,
                    from_data=from_data,
                    to_data=to_data,
                    route_result=route_result,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code="ROUTING_NO_MATCHING_FILTER",
                    error_message=f"No route found for filter '{route_filter}'.",
                    selected_route_type=None,
                    selected_route=None,
                    unresolved_reason="routing_no_matching_filter",
                    ai_latency_ms=None,
                    routing_latency_ms=routing_latency_ms,
                    total_latency_ms=total_latency_ms,
                )
                return self._error_response(
                    request_id,
                    status.HTTP_404_NOT_FOUND,
                    "ROUTING_NO_MATCHING_FILTER",
                    f"No route found for filter '{route_filter}'.",
                )
            routing_latency_ms = (time.perf_counter() - routing_start) * 1000.0
            total_latency_ms = (time.perf_counter() - request_start) * 1000.0

            self._record_history(
                request=request,
                request_id=request_id,
                source_type=source_type,
                input_text=None,
                preference=route_filter,
                from_data=from_data,
                to_data=to_data,
                route_result=route_result,
                status_value=RouteHistory.STATUS_SUCCESS,
                error_code=None,
                error_message=None,
                selected_route_type=(selected_route or {}).get("type"),
                selected_route=selected_route,
                unresolved_reason=None,
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
                route_filter=route_filter,
                selected_route=selected_route,
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
                    request_id=request_id,
                    source_type=source_type,
                    input_text=text_query,
                    preference=route_filter,
                    from_data=None,
                    to_data=None,
                    route_result=None,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code=error_code,
                    error_message=error.details,
                    selected_route_type=None,
                    unresolved_reason="ai_error",
                    ai_latency_ms=ai_latency_ms,
                    routing_latency_ms=None,
                    total_latency_ms=total_latency_ms,
                )
                return self._error_response(
                    request_id, http_status, error_code, error.details
                )

            ai_latency_ms = (time.perf_counter() - ai_start) * 1000.0
            if not ai_result:
                total_latency_ms = (time.perf_counter() - request_start) * 1000.0
                self._record_history(
                    request=request,
                    request_id=request_id,
                    source_type=source_type,
                    input_text=text_query,
                    preference=route_filter,
                    from_data=None,
                    to_data=None,
                    route_result=None,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code="AI_EMPTY_RESULT",
                    error_message="AI service returned no coordinates.",
                    selected_route_type=None,
                    unresolved_reason="ai_empty",
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

            if "from_lat" in ai_result and "from_lon" in ai_result:
                source_lat = ai_result["from_lat"]
                source_lon = ai_result["from_lon"]
                from_name = ai_result.get("from_location")
            elif current_location is not None:
                source_lat, source_lon = current_location
                from_name = "current_location"
            else:
                total_latency_ms = (time.perf_counter() - request_start) * 1000.0
                self._record_history(
                    request=request,
                    request_id=request_id,
                    source_type=source_type,
                    input_text=text_query,
                    preference=route_filter,
                    from_data=None,
                    to_data=None,
                    route_result=None,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code="SOURCE_REQUIRED_OR_CURRENT_LOCATION",
                    error_message="Source location is missing. Provide current_location.",
                    selected_route_type=None,
                    unresolved_reason="missing_source",
                    ai_latency_ms=ai_latency_ms,
                    routing_latency_ms=None,
                    total_latency_ms=total_latency_ms,
                )
                return self._error_response(
                    request_id,
                    status.HTTP_400_BAD_REQUEST,
                    "SOURCE_REQUIRED_OR_CURRENT_LOCATION",
                    "Source location is missing. Provide current_location.",
                )

            from_data = {
                "name": from_name,
                "lat": source_lat,
                "lon": source_lon,
            }
            to_data = {
                "name": ai_result.get("to_location"),
                "lat": ai_result["to_lat"],
                "lon": ai_result["to_lon"],
            }

            routing_start = time.perf_counter()
            try:
                route_result = self.routing_client.get_route(
                    source_lat,
                    source_lon,
                    ai_result["to_lat"],
                    ai_result["to_lon"],
                )
            except RoutingGrpcClientError as error:
                routing_latency_ms = (time.perf_counter() - routing_start) * 1000.0
                total_latency_ms = (time.perf_counter() - request_start) * 1000.0
                http_status, error_code = self._map_routing_error(error)
                self._record_history(
                    request=request,
                    request_id=request_id,
                    source_type=source_type,
                    input_text=text_query,
                    preference=route_filter,
                    from_data=from_data,
                    to_data=to_data,
                    route_result=None,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code=error_code,
                    error_message=error.details,
                    selected_route_type=None,
                    unresolved_reason="routing_error",
                    ai_latency_ms=ai_latency_ms,
                    routing_latency_ms=routing_latency_ms,
                    total_latency_ms=total_latency_ms,
                )
                return self._error_response(
                    request_id, http_status, error_code, error.details
                )

            route_result, selected_route = self._select_route(
                route_result, route_filter
            )
            if selected_route is None:
                routing_latency_ms = (time.perf_counter() - routing_start) * 1000.0
                total_latency_ms = (time.perf_counter() - request_start) * 1000.0
                self._record_history(
                    request=request,
                    request_id=request_id,
                    source_type=source_type,
                    input_text=text_query,
                    preference=route_filter,
                    from_data=from_data,
                    to_data=to_data,
                    route_result=route_result,
                    status_value=RouteHistory.STATUS_FAILED,
                    error_code="ROUTING_NO_MATCHING_FILTER",
                    error_message=f"No route found for filter '{route_filter}'.",
                    selected_route_type=None,
                    selected_route=None,
                    unresolved_reason="routing_no_matching_filter",
                    ai_latency_ms=ai_latency_ms,
                    routing_latency_ms=routing_latency_ms,
                    total_latency_ms=total_latency_ms,
                )
                return self._error_response(
                    request_id,
                    status.HTTP_404_NOT_FOUND,
                    "ROUTING_NO_MATCHING_FILTER",
                    f"No route found for filter '{route_filter}'.",
                )
            routing_latency_ms = (time.perf_counter() - routing_start) * 1000.0
            total_latency_ms = (time.perf_counter() - request_start) * 1000.0
            self._record_history(
                request=request,
                request_id=request_id,
                source_type=source_type,
                input_text=text_query,
                preference=route_filter,
                from_data=from_data,
                to_data=to_data,
                route_result=route_result,
                status_value=RouteHistory.STATUS_SUCCESS,
                error_code=None,
                error_message=None,
                selected_route_type=(selected_route or {}).get("type"),
                selected_route=selected_route,
                unresolved_reason=None,
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
                route_filter=route_filter,
                selected_route=selected_route,
            )

        total_latency_ms = (time.perf_counter() - request_start) * 1000.0
        self._record_history(
            request=request,
            request_id=request_id,
            source_type=RouteHistory.SOURCE_TEXT,
            input_text=data.get("text"),
            preference=route_filter,
            from_data=None,
            to_data=None,
            route_result=None,
            status_value=RouteHistory.STATUS_FAILED,
            error_code="INVALID_REQUEST_BODY",
            error_message="Provide either 'text' or both 'origin' and 'destination'.",
            selected_route_type=None,
            unresolved_reason="invalid_body",
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


class RouteHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Routing"],
        summary="Get current user route history",
        responses={200: RouteHistoryItemSerializer(many=True)},
    )
    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 50))
        except (TypeError, ValueError):
            limit = 50
        limit = min(max(limit, 1), 100)
        entries = RouteHistory.objects.filter(user=request.user).order_by(
            "-created_at"
        )[:limit]

        payload = [
            {
                "request_id": item.request_id,
                "source_type": item.source_type,
                "input_text": item.input_text,
                "filter": item.preference,
                "selected_route_type": item.selected_route_type,
                "origin_name": item.origin_name,
                "destination_name": item.destination_name,
                "status": item.status,
                "error_code": item.error_code,
                "total_distance_meters": item.total_distance_meters,
                "total_duration_seconds": item.total_duration_seconds,
                "estimated_fare": item.estimated_fare,
                "walk_distance_meters": item.walk_distance_meters,
                "created_at": item.created_at,
            }
            for item in entries
        ]
        return Response(payload, status=status.HTTP_200_OK)
