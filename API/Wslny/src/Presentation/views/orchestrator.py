from django.conf import settings
import grpc
from uuid import uuid4
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
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

    def post(self, request):
        request_id = str(uuid4())

        if self.client_boot_error:
            return self._error_response(
                request_id,
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "API_CLIENT_BOOT_ERROR",
                self.client_boot_error,
            )

        if self.ai_client is None or self.routing_client is None:
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
            return self._error_response(
                request_id,
                status.HTTP_400_BAD_REQUEST,
                "INVALID_REQUEST_MODE",
                "Provide either text or origin/destination, not both.",
            )

        if has_coordinates:
            parsed = self._parse_coordinates(data)
            if parsed is None:
                return self._error_response(
                    request_id,
                    status.HTTP_400_BAD_REQUEST,
                    "INVALID_COORDINATES",
                    "Invalid coordinate format.",
                )

            s_lat, s_lon, d_lat, d_lon = parsed
            try:
                route_result = self.routing_client.get_route(
                    s_lat,
                    s_lon,
                    d_lat,
                    d_lon,
                )
            except RoutingGrpcClientError as error:
                http_status, error_code = self._map_routing_error(error)
                return self._error_response(
                    request_id,
                    http_status,
                    error_code,
                    error.details,
                )

            return self._success_response(
                request_id=request_id,
                source="map",
                route_result=route_result,
                from_data={"name": None, "lat": s_lat, "lon": s_lon},
                to_data={"name": None, "lat": d_lat, "lon": d_lon},
                intent="direct_coordinates",
            )

        if has_text:
            text_query = data["text"].strip()
            try:
                ai_result = self.ai_client.extract_route(text_query)
            except AiGrpcClientError as error:
                http_status, error_code = self._map_ai_error(error)
                return self._error_response(
                    request_id,
                    http_status,
                    error_code,
                    error.details,
                )

            if not ai_result:
                return self._error_response(
                    request_id,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "AI_EMPTY_RESULT",
                    "AI service returned no coordinates.",
                )

            try:
                route_result = self.routing_client.get_route(
                    ai_result["from_lat"],
                    ai_result["from_lon"],
                    ai_result["to_lat"],
                    ai_result["to_lon"],
                )
            except RoutingGrpcClientError as error:
                http_status, error_code = self._map_routing_error(error)
                return self._error_response(
                    request_id,
                    http_status,
                    error_code,
                    error.details,
                )

            return self._success_response(
                request_id=request_id,
                source="text",
                route_result=route_result,
                from_data={
                    "name": ai_result.get("from_location"),
                    "lat": ai_result["from_lat"],
                    "lon": ai_result["from_lon"],
                },
                to_data={
                    "name": ai_result.get("to_location"),
                    "lat": ai_result["to_lat"],
                    "lon": ai_result["to_lon"],
                },
                intent=ai_result.get("intent", "unknown"),
            )

        return self._error_response(
            request_id,
            status.HTTP_400_BAD_REQUEST,
            "INVALID_REQUEST_BODY",
            "Provide either 'text' or both 'origin' and 'destination'.",
        )
