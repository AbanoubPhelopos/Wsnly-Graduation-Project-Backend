from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from src.Infrastructure.GrpcClients.ai_client import AiGrpcClient
from src.Infrastructure.GrpcClients.routing_client import RoutingGrpcClient


class RouteOrchestratorView(APIView):
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

    def post(self, request):
        if self.client_boot_error:
            return Response(
                {"error": self.client_boot_error},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if self.ai_client is None or self.routing_client is None:
            return Response(
                {"error": "gRPC clients are not available."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        data = request.data

        has_text = (
            isinstance(data.get("text"), str) and data.get("text", "").strip() != ""
        )
        has_coordinates = "origin" in data and "destination" in data

        if has_text and has_coordinates:
            return Response(
                {"error": "Provide either text or origin/destination, not both."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if has_coordinates:
            parsed = self._parse_coordinates(data)
            if parsed is None:
                return Response(
                    {"error": "Invalid coordinate format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            s_lat, s_lon, d_lat, d_lon = parsed
            route_result = self.routing_client.get_route(s_lat, s_lon, d_lat, d_lon)

            if route_result:
                return Response(
                    {"source": "map", "route": route_result},
                    status=status.HTTP_200_OK,
                )

            return Response(
                {"error": "Routing Engine failed to find a path."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if has_text:
            text_query = data["text"].strip()
            ai_result = self.ai_client.extract_route(text_query)

            if not ai_result:
                return Response(
                    {"error": "AI Service could not understand the location."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            route_result = self.routing_client.get_route(
                ai_result["from_lat"],
                ai_result["from_lon"],
                ai_result["to_lat"],
                ai_result["to_lon"],
            )

            if route_result:
                return Response(
                    {
                        "source": "text",
                        "intent": ai_result.get("intent", "unknown"),
                        "from": {
                            "name": ai_result.get("from_location"),
                            "lat": ai_result["from_lat"],
                            "lon": ai_result["from_lon"],
                        },
                        "to": {
                            "name": ai_result.get("to_location"),
                            "lat": ai_result["to_lat"],
                            "lon": ai_result["to_lon"],
                        },
                        "route": route_result,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {"error": "Routing Engine failed to find a path."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"error": "Provide either 'text' or both 'origin' and 'destination'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
